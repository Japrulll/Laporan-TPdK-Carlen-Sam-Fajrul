from importlib import import_module
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_verified_model_is_inference_only_and_reproduces_notebook_test_confusions():
    try:
        module = import_module("adadeh.model")
    except ModuleNotFoundError:
        pytest.fail("Loader model asli belum tersedia", pytrace=False)
    runtime = module.ModelRuntime.load(ROOT / "artifacts" / "kaggle_output")
    assert runtime.model.input_shape == (None, 128, 157, 1)
    assert runtime.model.output_shape == (None, 2)
    assert runtime.model.count_params() == 110114
    assert runtime.model.compiled is False
    with np.load(ROOT / "artifacts" / "kaggle_output" / "test.npz", allow_pickle=False) as data:
        scores = runtime.predict_raw_features(data["array"])
        labels, ids = data["label"], data["file_id"]
        from sklearn.metrics import confusion_matrix, roc_auc_score
        actual = confusion_matrix(labels, scores > runtime.contract.threshold)
        np.testing.assert_array_equal(actual, [[299, 6], [0, 202]])
        np.testing.assert_allclose(roc_auc_score(labels, scores), 0.9987015094952119, atol=1e-7)
        files = np.unique(ids)
        file_scores = np.array([scores[ids == f].mean() for f in files])
        file_labels = np.array([labels[ids == f][0] for f in files])
        np.testing.assert_array_equal(confusion_matrix(file_labels, file_scores > runtime.contract.threshold), [[136, 4], [0, 140]])
        np.testing.assert_allclose(roc_auc_score(file_labels, file_scores), 0.9971428571428571, atol=1e-7)
        first = runtime.predict_raw_features(data["array"][:4])
        second = runtime.predict_raw_features(data["array"][:4])
        np.testing.assert_allclose(first, second, rtol=1e-5, atol=1e-6)
    assert runtime.version.startswith("adadeh_cnn-")
