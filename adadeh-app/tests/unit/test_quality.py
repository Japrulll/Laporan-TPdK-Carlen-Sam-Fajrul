from importlib import import_module

import numpy as np
import pytest


def test_quality_warnings_are_separate_and_never_change_waveform():
    try:
        module = import_module("adadeh.quality")
    except ModuleNotFoundError:
        pytest.fail("Penilaian mutu terpisah belum tersedia", pytrace=False)
    silent = np.zeros((2, 40000), dtype=np.float32)
    original = silent.copy()
    warnings = module.assess_quality(silent, 16000)
    assert any("hening" in text for text in warnings)
    assert any("rendah" in text for text in warnings)
    np.testing.assert_array_equal(silent, original)


def test_quality_detects_clipping_but_does_not_flag_healthy_level():
    module = import_module("adadeh.quality")
    clipped = np.ones((1, 80000), dtype=np.float32)
    assert any("clipping" in text for text in module.assess_quality(clipped, 16000))
    t = np.arange(80000, dtype=np.float32) / 16000
    healthy = (0.2 * np.sin(2 * np.pi * 440 * t))[None, :]
    assert module.assess_quality(healthy, 16000) == []
