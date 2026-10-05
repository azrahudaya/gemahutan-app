"""Embedding classifier engine (Track B): BirdNET 1024-dim embedding + trained MLP."""
import json
import os
from pathlib import Path

import numpy as np

from ml.engines.base import DetectionResult, InferenceEngine

ML_DIR = Path(__file__).parent.parent
CHECKPOINT_DIR = Path(os.getenv("GEMAHUTAN_CHECKPOINT_DIR", str(ML_DIR / "checkpoints")))
EMB_DIR = Path(os.getenv("GEMAHUTAN_EMB_DIR", str(ML_DIR / "embeddings")))

EMBEDDING_TENSOR_INDEX = 545  # BirdNET GLOBAL_AVG_POOL
SR = 48000
SEGMENT_DURATION = 3.0


class EmbeddingClassifierEngine(InferenceEngine):
    def __init__(self):
        self._model = None
        self._label_map = None
        self._inv_label_map = None
        self._mean = None
        self._std = None
        self._interp = None
        # Vector scaling calibration (T + per-class bias). Default identity
        # kalau temperature.json belum ada atau gagal dimuat.
        self._temperature = 1.0
        self._bias = None

    def _load_calibration(self):
        # Sumber 1: bundle arrays di best_model.npz (sumber utama).
        model_path = CHECKPOINT_DIR / "best_model.npz"
        if model_path.exists():
            try:
                data = np.load(model_path)
                if "temperature" in data.files:
                    self._temperature = float(data["temperature"][0])
                if "bias" in data.files:
                    self._bias = np.asarray(data["bias"], dtype=np.float32)
                if "temperature" in data.files:
                    return
            except Exception:
                pass
        # Sumber 2: temperature.json sidecar (fallback kompatibilitas).
        cal_path = CHECKPOINT_DIR / "temperature.json"
        if cal_path.exists():
            try:
                data = json.loads(cal_path.read_text())
                self._temperature = float(data.get("temperature", 1.0))
                bias = data.get("bias")
                if bias is not None:
                    self._bias = np.array(bias, dtype=np.float32)
            except Exception:
                self._temperature = 1.0
                self._bias = None

    def _ensure_loaded(self):
        if self._model is not None:
            return
        from ml.train import MLP

        # Load label map
        with open(EMB_DIR / "label_map.json") as f:
            self._label_map = json.load(f)
        self._inv_label_map = {v: k for k, v in self._label_map.items()}

        # Load normalization
        norm = np.load(CHECKPOINT_DIR / "normalization.npz")
        self._mean = norm["mean"]
        self._std = norm["std"]

        # Load MLP (input_dim=1024 for BirdNET embeddings)
        num_classes = len(self._label_map)
        input_dim = len(self._mean)  # 1024
        hidden_dim = 256
        self._model = MLP(input_dim, hidden_dim, num_classes)
        self._model.load(str(CHECKPOINT_DIR / "best_model.npz"))
        # Pengaman eksplisit: dropout harus mati saat inference. MLP.load()
        # sudah menyetel ini, tetapi baris ini dipertahankan supaya mesin
        # produksi tidak bergantung pada perilaku internal kelas latih.
        self._model.training = False

        # Load vector-scaling calibration (temperature + bias)
        self._load_calibration()

        # Load BirdNET TFLite for embedding extraction
        self._load_birdnet_interpreter()

    def _load_birdnet_interpreter(self):
        """Load BirdNET TFLite model for embedding extraction."""
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        import warnings
        warnings.filterwarnings('ignore')
        import tensorflow as tf

        # Find model path
        model_path = None
        try:
            from birdnetlib.analyzer import Analyzer
            a = Analyzer()
            model_path = a.model_path
        except Exception:
            import site
            for sp in site.getsitepackages():
                p = Path(sp) / "birdnetlib" / "models" / "analyzer" / "BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite"
                if p.exists():
                    model_path = str(p)
                    break

        if not model_path:
            raise FileNotFoundError("BirdNET TFLite model not found")

        self._interp = tf.lite.Interpreter(
            model_path=model_path,
            experimental_preserve_all_tensors=True,
        )
        self._interp.allocate_tensors()

    def _extract_embedding(self, audio_segment: np.ndarray) -> np.ndarray:
        """Extract 1024-dim BirdNET embedding from audio segment."""
        input_details = self._interp.get_input_details()
        audio_input = audio_segment.reshape(1, -1).astype(np.float32)
        self._interp.set_tensor(input_details[0]['index'], audio_input)
        self._interp.invoke()
        embedding = self._interp.get_tensor(EMBEDDING_TENSOR_INDEX)
        return embedding.reshape(-1)

    def _raw_logits(self, emb_norm):
        """Forward pass returning pre-softmax logits (vector scaling input)."""
        z1 = emb_norm @ self._model.W1 + self._model.b1
        a1 = np.maximum(0, z1) if self._model.activation == "relu" else z1
        z2 = a1 @ self._model.W2 + self._model.b2
        return z2

    def _calibrated_probs(self, emb_norm):
        """Logits -> vector-scaled softmax probabilities."""
        z = self._raw_logits(emb_norm)
        if self._bias is not None and z.ndim == 1:
            z = z + self._bias
        elif self._bias is not None and z.ndim == 2:
            z = z + self._bias[None, :]
        z = z / self._temperature
        z = z - np.max(z, axis=-1, keepdims=True)
        ez = np.exp(z)
        return ez / np.sum(ez, axis=-1, keepdims=True)

    def name(self) -> str:
        return "EmbeddingClassifier"

    def version(self) -> str:
        return "2.0"

    def species_count(self) -> int:
        self._ensure_loaded()
        return len(self._label_map) - (1 if "_negative" in self._label_map else 0)

    def predict(self, audio_path: str, lat: float = None, lon: float = None,
                min_conf: float = 0.1) -> list[DetectionResult]:
        self._ensure_loaded()
        from ml.engines.streaming import durasi_audio, segmen_stream

        segment_len = int(SR * SEGMENT_DURATION)
        total_s = durasi_audio(audio_path)
        results = []

        for start_sample, segment in segmen_stream(audio_path, sr=SR):
            # Extract BirdNET embedding
            emb = self._extract_embedding(segment)

            # Normalize
            emb = (emb - self._mean) / self._std

            # Predict with MLP + vector-scaling calibration
            probs = self._calibrated_probs(emb.reshape(1, -1))[0]
            top_idx = np.argsort(probs)[::-1]

            start_s = start_sample / SR
            end_s = min((start_sample + segment_len) / SR, total_s) if total_s > 0 else (start_sample + segment_len) / SR

            for idx in top_idx[:3]:
                conf = float(probs[idx])
                if conf < min_conf:
                    break
                species = self._inv_label_map.get(idx, "unknown")
                if species == "_negative":
                    continue
                results.append(DetectionResult(
                    species_scientific=species,
                    species_common=species,
                    confidence=conf,
                    start_s=round(start_s, 2),
                    end_s=round(end_s, 2),
                    engine=self.name(),
                    engine_version=self.version(),
                ))

        return results

    def predict_embedding(self, audio_path: str) -> list[dict]:
        """Return raw predictions with embeddings for cascade use."""
        self._ensure_loaded()
        from ml.engines.streaming import durasi_audio, segmen_stream

        segment_len = int(SR * SEGMENT_DURATION)
        total_s = durasi_audio(audio_path)
        results = []

        for start_sample, segment in segmen_stream(audio_path, sr=SR):
            emb = self._extract_embedding(segment)
            emb_norm = (emb - self._mean) / self._std
            probs = self._calibrated_probs(emb_norm)

            start_s = start_sample / SR
            end_s = min((start_sample + segment_len) / SR, total_s) if total_s > 0 else (start_sample + segment_len) / SR

            results.append({
                "start_s": round(start_s, 2),
                "end_s": round(end_s, 2),
                "probs": probs,
                "label_map": self._label_map,
                "inv_label_map": self._inv_label_map,
            })

        return results
