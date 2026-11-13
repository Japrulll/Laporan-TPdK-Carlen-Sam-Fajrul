"""Pembanding transkripsi langsung sel 8/11; bukan paritas data emas Kaggle."""
from pathlib import Path

import librosa
import numpy as np
import pytest
import torch
import torchaudio

from adadeh.contracts import ModelContract
from adadeh.preprocessing import extract_features


ROOT = Path(__file__).resolve().parents[2]


def notebook_reference(samples, sample_rate, contract):
    """Transkripsi independen sel 11, tanpa menjalankan notebook/pelatihan."""
    wav = samples.mean(0, keepdim=True)
    if sample_rate != contract.global_sr:
        wav = torchaudio.functional.resample(wav, sample_rate, contract.global_sr)
    y = wav.squeeze(0).numpy()
    n = (len(y) - contract.chunk_dur) // contract.step + 1
    n = min(n, contract.max_chunks)
    arrays = []
    for i in range(n):
        start = i * contract.step
        end = start + contract.chunk_dur
        chunk = y[start:end]
        mel = librosa.feature.melspectrogram(
            y=chunk, sr=contract.global_sr, n_fft=contract.n_fft,
            hop_length=contract.hop_length, n_mels=contract.n_mels,
            fmax=contract.global_sr // 2,
        )
        mel_db = librosa.power_to_db(mel, ref=1.0, top_db=80)
        arrays.append(mel_db)
    return np.stack(arrays).astype(np.float32)


def test_initial_complete_chunk_matches_notebook_transcription():
    contract = ModelContract.load(ROOT / "artifacts/kaggle_output/meta.json")
    samples = torch.linspace(-0.6, 0.8, 40000).reshape(1, -1)
    before = samples.clone()
    expected = notebook_reference(samples, 16000, contract)
    result = extract_features(samples, 16000, contract)
    assert result.raw.dtype == np.float32
    assert result.raw.shape == (1, 128, 157)
    np.testing.assert_array_equal(result.raw, expected)
    assert result.chunk_count == 1
    assert result.coverage_seconds == 2.5
    torch.testing.assert_close(samples, before, rtol=0, atol=0)


@pytest.mark.parametrize("length", [39999, 40000, 40001])
def test_complete_window_boundaries_do_not_pad(length):
    contract = ModelContract.load(ROOT / "artifacts/kaggle_output/meta.json")
    samples = torch.zeros((1, length), dtype=torch.float32)
    if length < 40000:
        with pytest.raises(ValueError, match="potongan utuh"):
            extract_features(samples, 16000, contract)
    else:
        batch = extract_features(samples, 16000, contract)
        assert batch.chunk_count == 1
        assert batch.coverage_seconds == 2.5
        np.testing.assert_array_equal(batch.raw, notebook_reference(samples, 16000, contract))


@pytest.mark.parametrize("sample_rate,length", [(16000, 180001), (22050, 137814), (48000, 300003)])
def test_stereo_resampling_four_initial_windows_and_unchanged_waveform(sample_rate, length):
    contract = ModelContract.load(ROOT / "artifacts/kaggle_output/meta.json")
    time = torch.arange(length, dtype=torch.float32) / sample_rate
    samples = torch.stack((0.3 * torch.sin(421 * time), 0.2 * torch.cos(811 * time)))
    before = samples.clone()
    result = extract_features(samples, sample_rate, contract)
    np.testing.assert_array_equal(result.raw, notebook_reference(samples, sample_rate, contract))
    assert result.raw.shape == (4, 128, 157)
    assert result.chunk_count == 4
    assert result.coverage_seconds == 6.25
    torch.testing.assert_close(samples, before, rtol=0, atol=0)


def test_rejects_nonfinite_samples_with_indonesian_error():
    contract = ModelContract.load(ROOT / "artifacts/kaggle_output/meta.json")
    samples = torch.zeros((1, 40000), dtype=torch.float32)
    samples[0, 100] = float("nan")
    with pytest.raises(ValueError, match="nilai tidak hingga"):
        extract_features(samples, 16000, contract)


@pytest.mark.parametrize("samples,sample_rate,message", [
    (torch.zeros(40000), 16000, "kanal, waktu"),
    (torch.zeros((0, 40000)), 16000, "kanal, waktu"),
    (torch.zeros((1, 40000), dtype=torch.int16), 16000, "float32 CPU"),
    (torch.zeros((1, 40000), dtype=torch.float64), 16000, "float32 CPU"),
    (torch.zeros((1, 40000)), 0, "laju sampel"),
])
def test_rejects_invalid_waveform_contract_with_indonesian_errors(samples, sample_rate, message):
    contract = ModelContract.load(ROOT / "artifacts/kaggle_output/meta.json")
    with pytest.raises(ValueError, match=message):
        extract_features(samples, sample_rate, contract)


@pytest.mark.parametrize("length,count", [
    (59999, 1), (60000, 2), (79999, 2), (80000, 3), (99999, 3), (100000, 4), (120000, 4),
])
def test_every_complete_window_boundary_and_initial_cap(length, count):
    contract = ModelContract.load(ROOT / "artifacts/kaggle_output/meta.json")
    samples = torch.linspace(-0.5, 0.2, length).reshape(1, -1)
    result = extract_features(samples, 16000, contract)
    assert result.chunk_count == count
    np.testing.assert_array_equal(result.raw, notebook_reference(samples, 16000, contract))


def test_ignored_tail_cannot_change_features():
    contract = ModelContract.load(ROOT / "artifacts/kaggle_output/meta.json")
    samples = torch.zeros((1, 160000), dtype=torch.float32)
    baseline = extract_features(samples, 16000, contract)
    samples[:, 100000:] = 0.999
    changed = extract_features(samples, 16000, contract)
    assert baseline.coverage_seconds == changed.coverage_seconds == 6.25
    np.testing.assert_array_equal(baseline.raw, changed.raw)
