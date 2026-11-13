"""Kesetaraan empat kandidat publik dengan fitur NPZ, bukan identitas audio emas.

FLAC berasal dari cache viewer HF; identitas waveform pelatihan tidak diasumsikan.
Uji ini tidak mengukur akurasi dan tidak melakukan pelatihan ulang.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from adadeh.audio import decode_audio
from adadeh.contracts import ModelContract
from adadeh.preprocessing import extract_features


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIRECTORY = ROOT / "artifacts/reference_audio"


@pytest.mark.parity
@pytest.mark.integration
@pytest.mark.parametrize("file_id", [1, 933, 40, 201])
def test_public_reference_features_match_original_test_npz(file_id):
    manifest = json.loads((REFERENCE_DIRECTORY / "manifest.json").read_text(encoding="utf-8"))
    entry = next(item for item in manifest["files"] if item["file_id"] == file_id)
    path = REFERENCE_DIRECTORY / entry["path"]
    payload = path.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == entry["sha256"]
    contract = ModelContract.load(ROOT / "artifacts/kaggle_output/meta.json")
    decoded = decode_audio(payload, path.name)
    features = extract_features(decoded.samples, decoded.sample_rate, contract)
    with np.load(ROOT / "artifacts/kaggle_output/test.npz", allow_pickle=False) as archive:
        expected = archive["array"][archive["file_id"] == file_id]
    assert features.raw.shape == expected.shape
    np.testing.assert_allclose(features.raw, expected, rtol=1e-5, atol=1e-5)
