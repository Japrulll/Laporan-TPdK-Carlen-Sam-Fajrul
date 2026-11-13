from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np

from adadeh.contracts import ModelContract

MODEL_SHA256 = "adffd47c27d7dd14eca8d91e4de22dc366ab5d92d4e51c02138ab04e0863eb30"
META_SHA256 = "43ee9cb4331edc86b73f2a9b22c11461b949d61a7aedf9aa0d164f6cc8fcd793"
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "kaggle_output"


class ModelArtifactError(RuntimeError):
    """Artefak tidak tersedia atau tidak cocok dengan kontrak yang disetujui."""


def _check_hash(path: Path, expected: str) -> None:
    if not path.is_file():
        raise ModelArtifactError("Artefak model belum tersedia. Unduh keluaran Kaggle sesuai README.")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ModelArtifactError("Integritas artefak berbeda dari model yang disetujui. Jangan gunakan fallback.")


def _custom_objects() -> dict[str, Any]:
    import tensorflow as tf
    from keras import layers

    class SpecAugment(layers.Layer):
        def __init__(self, time_mask=20, freq_mask=16, **kw):
            super().__init__(**kw)
            self.tm, self.fm = time_mask, freq_mask

        def _mask(self, B, n, limit, shape):
            w = tf.random.uniform([B, 1, 1, 1], 0, limit, dtype=tf.int32)
            s = tf.cast(tf.random.uniform([B, 1, 1, 1]) * tf.cast(n - w, tf.float32), tf.int32)
            r = tf.reshape(tf.range(n), shape)
            return (r >= s) & (r < s + w)

        def call(self, x, training=None):
            if not training:
                return x
            B, F, T = tf.shape(x)[0], tf.shape(x)[1], tf.shape(x)[2]
            mask = self._mask(B, F, self.fm, [1, -1, 1, 1]) | self._mask(B, T, self.tm, [1, 1, -1, 1])
            return tf.where(mask, tf.zeros_like(x), x)

    return {"SpecAugment": SpecAugment}


@dataclass
class ModelRuntime:
    model: Any
    contract: ModelContract
    version: str
    _lock: Any = field(default_factory=Lock, repr=False)

    @classmethod
    def load(cls, artifact_dir: str | Path = DEFAULT_ARTIFACT_DIR) -> "ModelRuntime":
        directory = Path(artifact_dir)
        model_path, meta_path = directory / "adadeh_cnn.keras", directory / "meta.json"
        _check_hash(model_path, MODEL_SHA256)
        _check_hash(meta_path, META_SHA256)
        from keras.models import load_model
        model = load_model(model_path, custom_objects=_custom_objects(), compile=False, safe_mode=True)
        contract = ModelContract.load(meta_path)
        if model.input_shape != (None, 128, 157, 1) or model.output_shape != (None, 2):
            raise ModelArtifactError("Bentuk input/output model tidak sesuai kontrak.")
        return cls(model, contract, f"adadeh_cnn-{MODEL_SHA256[:12]}-meta-{META_SHA256[:12]}")

    def predict_raw_features(self, raw: np.ndarray, batch_size: int = 32) -> np.ndarray:
        if batch_size < 1:
            raise ValueError("Ukuran batch harus positif.")
        features = self.contract.normalize(raw)
        if features.ndim != 4 or features.shape[1:] != (128, 157, 1) or not len(features):
            raise ValueError("Fitur harus berukuran (n, 128, 157) dengan n positif.")
        if not np.isfinite(features).all():
            raise ValueError("Fitur mengandung nilai tidak valid.")
        with self._lock:
            outputs = [np.asarray(self.model(features[i:i+batch_size], training=False))[:, 1]
                       for i in range(0, len(features), batch_size)]
        scores = np.concatenate(outputs)
        if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
            raise ModelArtifactError("Skor model tidak valid.")
        return scores
