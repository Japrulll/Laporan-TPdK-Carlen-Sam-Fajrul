from dataclasses import dataclass

import librosa
import numpy as np
import torch
import torchaudio

from adadeh.contracts import ModelContract


@dataclass(frozen=True)
class FeatureBatch:
    """Mel-dB mentah sebelum normalisasi beserta cakupan potongan awal."""

    raw: np.ndarray
    coverage_seconds: float
    chunk_count: int


def extract_features(
    samples: torch.Tensor, sample_rate: int, contract: ModelContract
) -> FeatureBatch:
    """Ambil potongan utuh awal; ekor dibuang persis seperti sel 11."""
    if not isinstance(samples, torch.Tensor) or samples.ndim != 2 or samples.shape[0] < 1:
        raise ValueError("Sampel audio harus berbentuk (kanal, waktu) dengan sedikitnya satu kanal.")
    if samples.dtype != torch.float32 or samples.device.type != "cpu":
        raise ValueError("Sampel audio harus berupa tensor float32 CPU.")
    if not isinstance(sample_rate, int) or isinstance(sample_rate, bool) or sample_rate <= 0:
        raise ValueError("Nilai laju sampel audio harus berupa bilangan bulat positif.")
    if not torch.isfinite(samples).all():
        raise ValueError("Audio berisi nilai tidak hingga (NaN/Inf).")
    wav = samples.mean(0, keepdim=True)
    if sample_rate != contract.global_sr:
        wav = torchaudio.functional.resample(wav, sample_rate, contract.global_sr)
    y = wav.squeeze(0).numpy()
    count = min((len(y) - contract.chunk_dur) // contract.step + 1, contract.max_chunks)
    if count < 1:
        raise ValueError("Audio tidak memiliki satu potongan utuh; padding tidak diterapkan.")
    arrays = []
    for index in range(count):
        start = index * contract.step
        chunk = y[start : start + contract.chunk_dur]
        mel = librosa.feature.melspectrogram(
            y=chunk,
            sr=contract.global_sr,
            n_fft=contract.n_fft,
            hop_length=contract.hop_length,
            n_mels=contract.n_mels,
            fmax=contract.global_sr // 2,
        )
        arrays.append(librosa.power_to_db(mel, ref=1.0, top_db=80))
    return FeatureBatch(
        raw=np.stack(arrays).astype(np.float32),
        coverage_seconds=(contract.chunk_dur + (count - 1) * contract.step)
        / contract.global_sr,
        chunk_count=count,
    )
