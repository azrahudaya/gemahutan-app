"""Cascade engine: BirdNET (Track A) + Embedding Classifier (Track B) combined.

Pipeline:
1. BirdNET detects species globally with temporal positions
2. Embedding classifier re-scores segments for 25 Indonesian species
3. Merger picks the best confidence per segment:
   - Indonesian species: use Track B score (more accurate locally)
   - Other species: keep Track A score
4. Apply per-species thresholds, merge adjacent segments
"""
import json
import logging
import os
from collections.abc import Callable
from pathlib import Path

import numpy as np
import yaml

from ml.ambang import muat_ambang
from ml.engines.base import DetectionResult, InferenceEngine


def daftar_spesies_target(label_map: dict) -> set[str]:
    """Daftar spesies TARGET, dari ml/data/species_list.json kalau ada.

    Dipisah jadi fungsi supaya bisa diuji tanpa memuat bobot BirdNET. Argumen
    label_map hanya dipakai sebagai jalur cadangan kalau species_list.json
    hilang, supaya engine tetap jalan di lingkungan yang datanya tidak lengkap.
    """
    daftar = ML_DIR / "data" / "species_list.json"
    if daftar.exists():
        with open(daftar) as f:
            return {e["scientific_name"] for e in json.load(f)}
    return {k for k in label_map if k != "_negative"}

logger = logging.getLogger(__name__)

ML_DIR = Path(__file__).parent.parent
THRESHOLDS_FILE = Path(os.getenv("GEMAHUTAN_THRESHOLDS_FILE", str(ML_DIR / "reports" / "thresholds.json")))
CONFIG_FILE = Path(os.getenv("GEMAHUTAN_CASCADE_CONFIG", str(ML_DIR / "configs" / "cascade.yaml")))

# Penyaring deteksi lemah. Diukur pada korpus lapangan, 61,7 persen jendela dari
# spesies di luar daftar model memicu deteksi di atas ambangnya, jadi ambang saja
# tidak cukup. Dua syarat di bawah menekan kedipan sinyal dan tebakan sekali muncul:
# potongan lebih pendek dari MIN_DURASI_S biasanya hanya bocoran energi, dan
# spesies dengan keyakinan di bawah AMBANG_KUAT harus muncul di beberapa potongan
# berbeda dalam satu rekaman supaya dianggap deteksi.
MIN_DURASI_S = 1.0
MIN_KEMUNCULAN_ULANG = 2
AMBANG_KUAT = 0.5


def muat_konfigurasi() -> dict:
    """Baca konfigurasi cascade dari YAML. Fallback ke default kalau gagal."""
    default = {
        "ambang_birdnet_nontarget": 0.1,
        "trackb_wajib_birdnet": False,
        "margin_top1_top2": 0.0,
        "pakai_energi": False,
        "ambang_energi": 0.0,
        "min_kemunculan_ulang": 2,
        "ambang_kuat": 0.5,
        "min_durasi_s": 1.0,
        "trackb_konfirmasi_topk": 0,       # 0 = nonaktif, 1/3/5/10 = aktif
        "trackb_konfirmasi_skor_min": 0.0,  # 0.0 = nonaktif
        "trackb_konfirmasi_skor_min_lunak": 0.0,  # 0.0 = nonaktif, >= 0.5 = konfirmasi lunak
    }
    if CONFIG_FILE.exists():
        try:
            cfg = yaml.safe_load(CONFIG_FILE.read_text()) or {}
            default.update(cfg)
        except Exception as e:
            logger.warning("gagal baca cascade.yaml: %s", e)
    return default


class CascadeEngine(InferenceEngine):
    def __init__(self):
        self._birdnet = None
        self._embed_clf = None
        self._thresholds = None
        self._indonesian_species = None
        self._cfg = {
            "ambang_birdnet_nontarget": 0.1,
            "trackb_wajib_birdnet": False,
            "margin_top1_top2": 0.0,
            "pakai_energi": False,
            "ambang_energi": 0.0,
            "min_kemunculan_ulang": 2,
            "ambang_kuat": 0.5,
        }

    def _ensure_loaded(self):
        if self._birdnet is not None:
            return

        from ml.engines.birdnet import BirdNetEngine
        from ml.engines.embedding_clf import EmbeddingClassifierEngine

        self._birdnet = BirdNetEngine()
        self._embed_clf = EmbeddingClassifierEngine()
        self._embed_clf._ensure_loaded()

        # Daftar spesies TARGET diambil dari ml/data/species_list.json, bukan dari
        # seluruh kunci label_map.
        #
        # Kenapa: label_map berisi setiap kelas yang dilatih, dan K4 (ML_10)
        # menambahkan kelas PEMICU yang justru harus diperlakukan NON-target
        # ("prediksi ke kelas pemicu = non-target"). Versi lama menyusun daftar
        # target dari semua kunci label_map minus _negative, jadi menambah kelas
        # pemicu akan membuat engine melaporkannya sebagai deteksi target, yaitu
        # kebalikan dari maksud K4, dan deteksi palsu akan NAIK tanpa ada yang
        # salah di modelnya.
        #
        # Perubahan ini NO-OP untuk produksi, dibuktikan bukan diasumsikan:
        # label_map produksi minus _negative == species_list.json, keduanya 25
        # spesies, tidak ada selisih di kedua arah. Dijaga test
        # ml/tests/test_daftar_target.py.
        self._indonesian_species = daftar_spesies_target(self._embed_clf._label_map)

        # Load per-species thresholds
        if THRESHOLDS_FILE.exists():
            self._thresholds = muat_ambang(THRESHOLDS_FILE)
        else:
            self._thresholds = {}

        # Load config cascade
        self._cfg = muat_konfigurasi()

    def name(self) -> str:
        return "CascadeEngine"

    def version(self) -> str:
        return "1.0"

    def species_count(self) -> int:
        self._ensure_loaded()
        return 6522 + self._embed_clf.species_count()

    def predict(self, audio_path: str, lat: float = None, lon: float = None,
                min_conf: float = 0.1,
                progress_cb: Callable[[str, int], None] | None = None) -> list[DetectionResult]:
        self._ensure_loaded()

        # Step 1: BirdNET detections (global, with temporal positions)
        birdnet_results = self._birdnet.predict(
            audio_path, lat=lat, lon=lon, min_conf=0.05  # lower threshold, we re-score
        )
        # BirdNET sudah selesai, tahap klasifikasi Track B menyusul. Worker
        # memakai ini untuk menulis progres 30 ke 60 sebelum klasifikasi mulai.
        if progress_cb is not None:
            progress_cb("birdnet", 60)

        # Step 2: Track B predictions per segment
        trackb_segments = self._embed_clf.predict_embedding(audio_path)

        # Step 3: Merge
        merged = []

        # Process BirdNET detections
        for det in birdnet_results:
            species = det.species_scientific

            if species in self._indonesian_species:
                # Re-score with Track B
                trackb_conf = self._find_trackb_confidence(
                    species, det.start_s, det.end_s, trackb_segments
                )
                if trackb_conf is not None:
                    # Use Track B confidence (more accurate for local species)
                    threshold = self._get_threshold(species)
                    if trackb_conf >= threshold:
                        merged.append(DetectionResult(
                            species_scientific=species,
                            species_common=det.species_common,
                            confidence=round(trackb_conf, 4),
                            start_s=det.start_s,
                            end_s=det.end_s,
                            engine="CascadeEngine(B)",
                            engine_version=self.version(),
                        ))
                else:
                    # Track B didn't have this segment, keep BirdNET
                    threshold = self._get_threshold(species)
                    if det.confidence >= threshold:
                        merged.append(DetectionResult(
                            species_scientific=species,
                            species_common=det.species_common,
                            confidence=det.confidence,
                            start_s=det.start_s,
                            end_s=det.end_s,
                            engine="CascadeEngine(A)",
                            engine_version=self.version(),
                        ))
            else:
                # Non-Indonesian species: keep BirdNET hanya di atas ambang non-target
                ambang_nontarget = self._cfg.get("ambang_birdnet_nontarget", 0.1)
                if det.confidence >= ambang_nontarget:
                    merged.append(DetectionResult(
                        species_scientific=species,
                        species_common=det.species_common,
                        confidence=det.confidence,
                        start_s=det.start_s,
                        end_s=det.end_s,
                        engine="CascadeEngine(A)",
                        engine_version=self.version(),
                    ))

        # Step 4: Add Track B detections not found by BirdNET
        birdnet_species_times = set(
            (d.species_scientific, d.start_s) for d in merged
        )
        birdnet_species = set(d.species_scientific for d in birdnet_results)
        margin = self._cfg.get("margin_top1_top2", 0.0)
        wajib_birdnet = self._cfg.get("trackb_wajib_birdnet", False)
        konfirmasi_topk = int(self._cfg.get("trackb_konfirmasi_topk", 0))
        konfirmasi_skor_min = float(self._cfg.get("trackb_konfirmasi_skor_min", 0.0))

        # Bangun indeks BirdNET per jendela untuk konfirmasi bertingkat
        if konfirmasi_topk > 0 or konfirmasi_skor_min > 0:
            birdnet_per_window = self._bangun_indeks_birdnet(
                birdnet_results, konfirmasi_topk, konfirmasi_skor_min
            )
        else:
            birdnet_per_window = None

        for seg in trackb_segments:
            probs = seg["probs"]
            inv_map = seg["inv_label_map"]
            # Urutkan probabilitas; hitung margin top1-top2
            urutan = np.argsort(probs)[::-1]
            top_indices = urutan[:3]
            top1_conf = float(probs[urutan[0]]) if len(urutan) > 0 else 0.0
            top2_conf = float(probs[urutan[1]]) if len(urutan) > 1 else 0.0

            for idx in top_indices:
                species = inv_map.get(idx, "unknown")
                if species == "_negative":
                    continue
                conf = float(probs[idx])
                threshold = self._get_threshold(species)
                if conf < threshold:
                    continue
                # Margin top1-top2: hanya berlaku untuk deteksi top-1
                if idx == urutan[0] and (top1_conf - top2_conf) < margin:
                    continue
                # Konfirmasi lunak: kalau Track B sangat yakin (conf >= threshold), skip konfirmasi
                konfirmasi_skor_min_lunak = float(self._cfg.get("trackb_konfirmasi_skor_min_lunak", 0.0))
                if konfirmasi_skor_min_lunak > 0 and conf >= konfirmasi_skor_min_lunak:
                    # Konfirmasi lunak aktif dan conf >= threshold, skip konfirmasi BirdNET
                    pass
                else:
                    # Konfirmasi normal
                    # Konfirmasi BirdNET: spesies harus terdeteksi BirdNET
                    if wajib_birdnet and species not in birdnet_species:
                        continue
                    # Konfirmasi bertingkat: cek apakah BirdNET mengenali spesies ini
                    # di jendela yang tumpang tindih (topk atau skor_min)
                    if birdnet_per_window is not None:
                        if not self._cek_konfirmasi(
                            species, seg["start_s"], seg["end_s"], birdnet_per_window
                        ):
                            continue
                if (species, seg["start_s"]) in birdnet_species_times:
                    continue  # already covered

                merged.append(DetectionResult(
                    species_scientific=species,
                    species_common=species,
                    confidence=round(conf, 4),
                    start_s=seg["start_s"],
                    end_s=seg["end_s"],
                    engine="CascadeEngine(B)",
                    engine_version=self.version(),
                ))

        # Step 5: Merge adjacent segments (same species, gap < 2s)
        merged = self._merge_adjacent(merged)

        # Step 6: Buang deteksi lemah supaya hasil tidak penuh tebakan sekali muncul.
        merged = self._buang_deteksi_lemah(merged)

        # Sort by time
        merged.sort(key=lambda d: (d.start_s, -d.confidence))
        return merged

    def _buang_deteksi_lemah(self, detections: list[DetectionResult]) -> list[DetectionResult]:
        """Saring deteksi yang terlalu pendek atau terlalu lemah untuk berdiri sendiri."""
        min_durasi = self._cfg.get("min_durasi_s", MIN_DURASI_S)
        min_ulang = self._cfg.get("min_kemunculan_ulang", MIN_KEMUNCULAN_ULANG)
        ambang = self._cfg.get("ambang_kuat", AMBANG_KUAT)

        cukup_panjang = [
            d for d in detections if max(0.0, d.end_s - d.start_s) >= min_durasi
        ]

        jumlah_per_spesies: dict[str, int] = {}
        for d in cukup_panjang:
            jumlah_per_spesies[d.species_scientific] = (
                jumlah_per_spesies.get(d.species_scientific, 0) + 1
            )

        hasil = []
        dibuang_pendek = len(detections) - len(cukup_panjang)
        dibuang_lemah = 0
        for d in cukup_panjang:
            if (
                d.confidence < ambang
                and jumlah_per_spesies[d.species_scientific] < min_ulang
            ):
                dibuang_lemah += 1
                continue
            hasil.append(d)

        if dibuang_pendek or dibuang_lemah:
            logger.info(
                "penyaring deteksi: %d dibuang karena durasi < %.1fs, %d dibuang karena lemah dan hanya muncul sekali",
                dibuang_pendek,
                min_durasi,
                dibuang_lemah,
            )
        return hasil

    def _find_trackb_confidence(self, species, start_s, end_s, segments):
        """Find Track B confidence for a species in overlapping time segments."""
        label_map = segments[0]["label_map"] if segments else {}
        species_idx = label_map.get(species)
        if species_idx is None:
            return None

        best_conf = None
        for seg in segments:
            # Check time overlap
            overlap = min(end_s, seg["end_s"]) - max(start_s, seg["start_s"])
            if overlap > 0.5:  # at least 0.5s overlap
                conf = float(seg["probs"][species_idx])
                if best_conf is None or conf > best_conf:
                    best_conf = conf
        return best_conf

    def _get_threshold(self, species):
        """Get per-species threshold, default 0.15."""
        return float(self._thresholds.get(species, 0.15))

    def _merge_adjacent(self, detections):
        """Merge detections of same species with gap < 2 seconds."""
        if not detections:
            return detections

        by_species = {}
        for d in detections:
            by_species.setdefault(d.species_scientific, []).append(d)

        merged = []
        for _species, dets in by_species.items():
            dets.sort(key=lambda d: d.start_s)
            current = dets[0]
            for d in dets[1:]:
                if d.start_s - current.end_s < 2.0:
                    current = DetectionResult(
                        species_scientific=current.species_scientific,
                        species_common=current.species_common,
                        confidence=max(current.confidence, d.confidence),
                        start_s=current.start_s,
                        end_s=d.end_s,
                        engine=current.engine,
                        engine_version=current.engine_version,
                    )
                else:
                    merged.append(current)
                    current = d
            merged.append(current)

        return merged

    def _bangun_indeks_birdnet(
        self, birdnet_results: list[DetectionResult],
        topk: int, skor_min: float
    ) -> dict:
        """Bangun indeks per-jendela BirdNET untuk konfirmasi bertingkat.

        Return: dict keyed by (start_s, end_s) -> set of species yang lolos konfirmasi.
        Spesies masuk set jika:
          - topk > 0 dan spesies ada di top-k deteksi BirdNET di jendela itu, ATAU
          - skor_min > 0 dan skor BirdNET >= skor_min.
        """
        windows: dict[tuple[float, float], list[DetectionResult]] = {}
        for det in birdnet_results:
            key = (det.start_s, det.end_s)
            windows.setdefault(key, []).append(det)

        indeks: dict[tuple[float, float], set[str]] = {}
        for key, dets in windows.items():
            dets.sort(key=lambda d: -d.confidence)
            species_set: set[str] = set()
            for i, d in enumerate(dets):
                masuk = False
                if topk > 0 and i < topk:
                    masuk = True
                if skor_min > 0 and d.confidence >= skor_min:
                    masuk = True
                if masuk:
                    species_set.add(d.species_scientific)
            indeks[key] = species_set

        return indeks

    def _cek_konfirmasi(
        self, species: str, start_s: float, end_s: float,
        indeks: dict
    ) -> bool:
        """Cek apakah spesies dikonfirmasi BirdNET di jendela tumpang tindih."""
        for (ws, we), species_set in indeks.items():
            overlap = min(end_s, we) - max(start_s, ws)
            if overlap > 0.5 and species in species_set:
                return True
        return False

    def info(self) -> dict:
        self._ensure_loaded()
        return {
            "name": self.name(),
            "version": self.version(),
            "species_count": self.species_count(),
            "track_a": "BirdNET-Analyzer v2.4 (6522 species, zero-shot)",
            "track_b": f"EmbeddingClassifier v2.0 ({self._embed_clf.species_count()} Indonesian species, F1=0.60)",
            "pipeline": "cascade: BirdNET detects globally, custom MLP re-scores Indonesian species",
        }
