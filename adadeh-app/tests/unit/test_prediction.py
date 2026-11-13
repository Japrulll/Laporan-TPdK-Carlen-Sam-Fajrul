from importlib import import_module
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_prediction_uses_mean_fake_column_and_strict_exported_threshold():
    try:
        module = import_module("adadeh.prediction")
    except ModuleNotFoundError:
        pytest.fail("Agregasi prediksi belum tersedia", pytrace=False)
    from adadeh.contracts import ModelContract
    contract = ModelContract.load(ROOT / "artifacts/kaggle_output/meta.json")
    boundary = module.classify_scores(np.array([contract.threshold]), contract)
    assert boundary["predicted_class"] == "real"
    above = module.classify_scores(np.array([np.nextafter(contract.threshold, 1.0)]), contract)
    assert above["predicted_class"] == "fake"
    below_half = module.classify_scores(np.array([0.505]), contract)
    assert below_half["label"] == "Terindikasi asli"
    assert below_half["confidence"] == 0.505
    scores = np.array([0.1, 0.9, 0.8], dtype=np.float32)
    result = module.classify_scores(scores, contract)
    assert result["score_fake"] == float(scores.mean())
    for invalid in ([], [float("nan")], [-0.01], [1.01], [0.3] * 5):
        with pytest.raises(ValueError):
            module.classify_scores(np.asarray(invalid), contract)
