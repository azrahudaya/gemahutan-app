"""Base inference engine interface."""
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class DetectionResult:
    species_scientific: str
    species_common: str
    confidence: float
    start_s: float
    end_s: float
    engine: str
    engine_version: str


class InferenceEngine(ABC):
    """Abstract base for all inference engines."""

    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def version(self) -> str:
        ...

    @abstractmethod
    def species_count(self) -> int:
        ...

    @abstractmethod
    def predict(self, audio_path: str, lat: float = None, lon: float = None,
                min_conf: float = 0.1,
                progress_cb: Callable[[str, int], None] | None = None) -> list[DetectionResult]:
        """Jalankan inference pada satu berkas audio.

        Args:
            progress_cb: dipanggil engine di tengah proses dengan (tahap, progres),
                supaya worker bisa menulis jobs.progress sebelum inference selesai.
        """
        ...

    def info(self) -> dict:
        return {
            "name": self.name(),
            "version": self.version(),
            "species_count": self.species_count(),
        }
