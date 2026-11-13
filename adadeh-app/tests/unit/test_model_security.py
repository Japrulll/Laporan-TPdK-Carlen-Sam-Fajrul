from pathlib import Path

import pytest

from adadeh.model import ModelArtifactError, ModelRuntime


def test_loader_rejects_untrusted_model_without_using_best_checkpoint(tmp_path):
    (tmp_path / "best.keras").write_bytes(b"synthetic unit-test fixture, not a model")
    with pytest.raises(ModelArtifactError, match="belum tersedia"):
        ModelRuntime.load(tmp_path)
    (tmp_path / "adadeh_cnn.keras").write_bytes(b"synthetic corrupt model bytes")
    with pytest.raises(ModelArtifactError, match="Integritas"):
        ModelRuntime.load(tmp_path)
