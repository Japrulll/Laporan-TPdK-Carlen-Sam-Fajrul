import importlib
import json

import pytest


def test_download_reports_include_provenance_and_honest_coverage():
    try:
        module = importlib.import_module("adadeh.reporting")
    except ModuleNotFoundError:
        pytest.fail("Ekspor ringkasan belum tersedia", pytrace=False)
    result = {
        "file_name": "uji-á.wav", "duration_seconds": 10.0,
        "checked_at": "2026-01-01T00:00:00+00:00", "sha256": "a" * 64,
        "label": "Terindikasi asli", "score_fake": 0.2, "confidence": 0.8,
        "model_version": "synthetic-test-fixture", "limitations": ["Indikasi awal, bukan hasil forensik."],
        "analysis": {"chunk_count": 4, "start_seconds": 0.0, "end_seconds": 6.25, "coverage_seconds": 6.25, "complete": False},
        "warnings": ["Bagian akhir tidak dianalisis."],
    }
    encoded = module.to_json(result)
    assert json.loads(encoded) == result
    text = module.to_text(result).decode("utf-8")
    for required in ("uji-á.wav", "2026-01-01", "a" * 64, "Terindikasi asli", "synthetic-test-fixture", "forensik", "6,25", "tidak dianalisis"):
        assert required in text
    with pytest.raises(ValueError):
        module.to_json({})
