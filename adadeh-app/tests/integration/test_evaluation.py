from pathlib import Path
import json

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_evaluation_writes_real_baseline_metrics_and_local_scores(tmp_path):
    from adadeh import evaluation
    if not hasattr(evaluation, "evaluate_artifacts"):
        pytest.fail("Evaluasi artefak dan laporan belum tersedia", pytrace=False)
    report = evaluation.evaluate_artifacts(ROOT / "artifacts/kaggle_output", tmp_path)
    assert report["baseline_reproduced"] is True
    assert report["raw_audio_parity"]["status"] == "unverified"
    assert report["chunk"]["confusion_matrix"] == [[299, 6], [0, 202]]
    assert report["file"]["confusion_matrix"] == [[136, 4], [0, 140]]
    assert report["targets_file_level_pass"] is True
    assert report["training_performed"] is False
    assert json.loads((tmp_path / "test-report.json").read_text(encoding="utf-8")) == report
    assert (tmp_path / "local-score-reference.npz").exists()
