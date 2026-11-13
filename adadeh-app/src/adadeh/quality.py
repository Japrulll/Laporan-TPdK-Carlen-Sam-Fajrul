"""Indikator mutu engineering terpisah; tidak mentransformasi input model."""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class QualityPolicy:
    silence_dbfs: float = -50.0
    silence_fraction: float = 0.90
    low_level_dbfs: float = -35.0
    clipping_amplitude: float = 0.999
    clipping_fraction: float = 0.01
    frame_ms: int = 20
    short_duration_seconds: float = 3.75


DEFAULT_QUALITY_POLICY = QualityPolicy()


def assess_quality(samples: np.ndarray, sample_rate: int,
                   policy: QualityPolicy = DEFAULT_QUALITY_POLICY) -> list[str]:
    array = np.asarray(samples)
    if array.ndim not in (1, 2) or not array.size or sample_rate <= 0 or not np.isfinite(array).all():
        raise ValueError("Sampel audio untuk pemeriksaan mutu tidak valid.")
    mono = array.mean(axis=0, dtype=np.float32) if array.ndim == 2 else array
    warnings: list[str] = []
    rms = np.sqrt(np.einsum("i,i->", mono, mono, dtype=np.float64) / len(mono))
    dbfs = 20 * np.log10(max(float(rms), 1e-12))
    size = max(1, int(sample_rate * policy.frame_ms / 1000))
    count = len(mono) // size
    frames = mono[:count * size].reshape(count, size) if count else mono[None, :]
    energies = np.einsum("ij,ij->i", frames, frames, dtype=np.float64) / frames.shape[1]
    silent = np.sqrt(energies) < 10 ** (policy.silence_dbfs / 20)
    if float(silent.mean()) >= policy.silence_fraction:
        warnings.append("Rekaman didominasi keheningan menurut indikator mutu aplikasi; hasil perlu ditafsirkan dengan hati-hati.")
    if dbfs < policy.low_level_dbfs:
        warnings.append("Level sinyal rekaman sangat rendah; coba rekaman yang lebih jelas jika tersedia.")
    if np.count_nonzero(np.abs(array) >= policy.clipping_amplitude) / array.size >= policy.clipping_fraction:
        warnings.append("Terdeteksi indikasi clipping pada rekaman; distorsi dapat memengaruhi hasil.")
    if len(mono) / sample_rate < policy.short_duration_seconds:
        warnings.append("Rekaman relatif singkat dan hanya menyediakan satu potongan model; kesimpulan dapat kurang stabil.")
    return warnings
