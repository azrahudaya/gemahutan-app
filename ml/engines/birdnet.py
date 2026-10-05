"""BirdNET inference engine wrapper (streaming, hemat RAM).

Dulunya memakai `birdnetlib.Recording.analyze()` yang memuat SELURUH audio
via librosa.load. Rekaman 60 menit menghabiskan ~700 MB array, dan cascade
memuat audio beberapa kali sehingga RAM tembus 3,9 GB.

Sekarang memakai `Analyzer.predict(chunk)` per jendela 3 detik, dengan audio
dibaca per jendela lewat ml/engines/streaming.py. Paritas terverifikasi:
44/44 deteksi identik tanpa lokasi, 18/18 identik dengan filter lokasi Jawa.
"""
from collections.abc import Callable
from datetime import datetime

from ml.engines.base import DetectionResult, InferenceEngine
from ml.engines.streaming import segmen_stream

SAMPLE_RATE = 48000
SAMPLE_SECS = 3.0
OVERLAP = 0.0  # sama dengan default birdnetlib.Recording


class BirdNetEngine(InferenceEngine):
    def __init__(self):
        self._analyzer = None
        self._labels = None

    def _ensure_loaded(self):
        if self._analyzer is None:
            from birdnetlib.analyzer import Analyzer
            self._analyzer = Analyzer()
            self._labels = self._analyzer.labels

    def name(self) -> str:
        return "BirdNET-Analyzer"

    def version(self) -> str:
        return "2.4"

    def species_count(self) -> int:
        self._ensure_loaded()
        return len(self._labels)

    def _species_filter(self, lat, lon) -> set[str] | None:
        """Set label (ScientificName_CommonName) yang lolos filter lokasi."""
        if lat is None or lon is None:
            return None
        try:
            week = datetime.now().isocalendar()[1]
            species_list = self._analyzer.return_predicted_species_list(
                lon=lon, lat=lat, week_48=week
            )
            return set(species_list)
        except Exception:
            return None

    def predict(self, audio_path: str, lat: float = None, lon: float = None,
                min_conf: float = 0.1,
                progress_cb: Callable[[str, int], None] | None = None) -> list[DetectionResult]:
        self._ensure_loaded()
        species_set = self._species_filter(lat, lon)

        results = []
        for start_sample, segment in segmen_stream(
            audio_path, sr=SAMPLE_RATE, seg_dur=SAMPLE_SECS, overlap=OVERLAP
        ):
            pred = self._analyzer.predict(segment, sensitivity=1.0)[0]
            start_s = start_sample / SAMPLE_RATE
            end_s = start_s + SAMPLE_SECS

            urutan = sorted(range(len(pred)), key=lambda i: pred[i], reverse=True)
            for idx in urutan:
                conf = float(pred[idx])
                if conf < min_conf:
                    break
                label = self._labels[idx]
                if species_set is not None and label not in species_set:
                    continue
                parts = label.split("_", 1)
                scientific = parts[0]
                common = parts[1] if len(parts) > 1 else ""
                results.append(DetectionResult(
                    species_scientific=scientific,
                    species_common=common,
                    confidence=conf,
                    start_s=round(start_s, 2),
                    end_s=round(end_s, 2),
                    engine=self.name(),
                    engine_version=self.version(),
                ))

        if progress_cb is not None:
            progress_cb("birdnet", 60)

        return results


if __name__ == "__main__":
    import sys
    import time
    engine = BirdNetEngine()
    print(f"Engine: {engine.name()} v{engine.version()}")
    print(f"Species: {engine.species_count()}")
    if len(sys.argv) > 1:
        t0 = time.time()
        results = engine.predict(sys.argv[1])
        print(f"Detections: {len(results)} dalam {time.time()-t0:.1f}s")
        for r in results[:10]:
            print(f"  {r.species_common} ({r.species_scientific}): {r.confidence:.3f} [{r.start_s}-{r.end_s}s]")
