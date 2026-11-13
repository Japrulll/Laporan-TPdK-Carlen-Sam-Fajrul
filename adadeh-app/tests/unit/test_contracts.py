from importlib import import_module
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "kaggle_output"


def contracts():
    try:
        return import_module("adadeh.contracts")
    except ModuleNotFoundError:
        pytest.fail("Kontrak metadata aplikasi belum tersedia", pytrace=False)


def test_loads_exported_metadata_and_normalizes_without_mutating_input():
    module = contracts()
    contract = module.ModelContract.load(ARTIFACTS / "meta.json")
    assert contract.classes == ("real", "fake")
    assert contract.threshold == 0.5099999999999999
    assert (contract.global_sr, contract.chunk_dur, contract.step) == (16000, 40000, 20000)
    assert contract.max_chunks == 4
    raw = np.full((1, 128, 157), -28.0, dtype=np.float32)
    original = raw.copy()
    actual = contract.normalize(raw)
    expected = ((raw - contract.mu) / (contract.sd + 1e-8))[..., None]
    np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(raw, original)
    assert actual.shape == (1, 128, 157, 1)
    assert actual.dtype == np.float32


@pytest.mark.parametrize("values", [np.zeros((128, 157)), np.zeros((0, 128, 157)), np.full((1, 128, 157), np.nan)])
def test_normalization_rejects_invalid_feature_shape_or_values(values):
    contract = contracts().ModelContract.load(ARTIFACTS / "meta.json")
    with pytest.raises(ValueError):
        contract.normalize(values)
