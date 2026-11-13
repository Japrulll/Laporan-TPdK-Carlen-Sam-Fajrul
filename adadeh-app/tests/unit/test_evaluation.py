from importlib import import_module

import numpy as np
import pytest


def test_metrics_distinguish_eer_from_auc_and_operating_threshold_error():
    try:
        module = import_module("adadeh.evaluation")
    except ModuleNotFoundError:
        pytest.fail("Evaluasi model beku belum tersedia", pytrace=False)
    labels = np.array([0, 0, 1, 1])
    perfect = module.binary_metrics(labels, np.array([0.1, 0.2, 0.8, 0.9]), 0.51)
    assert perfect["eer"] == 0.0
    assert perfect["roc_auc"] == 1.0
    assert perfect["accuracy"] == 1.0
    assert perfect["f1_fake"] == 1.0
    assert perfect["confusion_matrix"] == [[2, 0], [0, 2]]
    ties = module.binary_metrics(labels, np.full(4, 0.5), 0.51)
    assert ties["eer"] == 0.5
    assert ties["roc_auc"] == 0.5
