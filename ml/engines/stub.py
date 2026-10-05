"""Stub inference engine for testing when real model is unavailable."""
from ml.engines.base import DetectionResult, InferenceEngine


class StubEngine(InferenceEngine):
    def name(self) -> str:
        return "StubEngine"

    def version(self) -> str:
        return "0.0.1"

    def species_count(self) -> int:
        return 0

    def predict(self, audio_path: str, lat: float = None, lon: float = None,
                min_conf: float = 0.1) -> list[DetectionResult]:
        return []
