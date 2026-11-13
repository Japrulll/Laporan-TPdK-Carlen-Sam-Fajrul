"""Agregasi per file dari sel 17; tidak melakukan penyesuaian threshold."""
import numpy as np

from adadeh.contracts import ModelContract


def classify_scores(scores: np.ndarray, contract: ModelContract) -> dict:
    values = np.asarray(scores)
    if (values.ndim != 1 or not 1 <= len(values) <= contract.max_chunks
            or not np.isfinite(values).all() or np.any((values < 0) | (values > 1))):
        raise ValueError("Skor harus berupa satu hingga empat probabilitas finite.")
    probability = float(values.mean())
    predicted = contract.classes[int(probability > contract.threshold)]
    return {
        "score_fake": probability,
        "confidence": max(probability, 1 - probability),
        "predicted_class": predicted,
        "label": "Terindikasi deepfake" if predicted == "fake" else "Terindikasi asli",
        "threshold": contract.threshold,
    }
