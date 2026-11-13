"""Kontrak numerik dari meta.json dan sel 8, 11, 16–17 notebook asli."""
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ModelContract:
    mu: float
    sd: float
    threshold: float
    global_sr: int
    chunk_dur: int
    step: int
    n_fft: int
    hop_length: int
    n_mels: int
    classes: tuple[str, str]
    max_chunks: int = 4

    @classmethod
    def load(cls, path: str | Path) -> "ModelContract":
        values = json.loads(Path(path).read_text(encoding="utf-8"))
        values["classes"] = tuple(values["classes"])
        return cls(**values)

    def normalize(self, raw: np.ndarray) -> np.ndarray:
        array = np.asarray(raw, dtype=np.float32)
        expected = (self.n_mels, 1 + self.chunk_dur // self.hop_length)
        if array.ndim != 3 or array.shape[1:] != expected or not len(array) or not np.isfinite(array).all():
            raise ValueError("Fitur mentah harus berukuran (n, 128, 157), bernilai finite, dengan n positif.")
        return ((array - self.mu) / (self.sd + 1e-8))[..., None]
