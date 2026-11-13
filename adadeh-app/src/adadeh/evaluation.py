"""Metrik model beku: EER interpolasi ROC, bukan error pada threshold operasi."""
import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score, roc_curve


def binary_metrics(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    labels, scores = np.asarray(labels), np.asarray(scores)
    predicted = scores > np.float64(threshold)
    fpr, tpr, _ = roc_curve(labels, scores, drop_intermediate=False)
    fnr = 1 - tpr
    difference = fpr - fnr
    i = int(np.flatnonzero(difference >= 0)[0])
    if i == 0:
        eer = float(fpr[0])
    else:
        weight = -difference[i - 1] / (difference[i] - difference[i - 1])
        eer = float(fpr[i - 1] + weight * (fpr[i] - fpr[i - 1]))
    return {
        "count": int(len(labels)),
        "confusion_matrix": confusion_matrix(labels, predicted, labels=[0, 1]).tolist(),
        "accuracy": float(accuracy_score(labels, predicted)),
        "f1_fake": float(f1_score(labels, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, scores)),
        "eer": eer,
        "eer_method": "interpolasi linear titik ROC ketika FPR = 1-TPR; drop_intermediate=False",
    }


def evaluate_artifacts(artifact_dir, output_dir) -> dict:
    """Evaluasi test terkunci; tidak memilih threshold dan tidak melatih model."""
    from pathlib import Path
    import hashlib
    import importlib.metadata
    import json
    import platform
    import sys
    import time
    from adadeh.model import ModelRuntime, MODEL_SHA256, META_SHA256

    started = time.perf_counter()
    directory, output = Path(artifact_dir), Path(output_dir)
    runtime = ModelRuntime.load(directory)
    test_path = directory / "test.npz"
    with np.load(test_path, allow_pickle=False) as data:
        scores = runtime.predict_raw_features(data["array"])
        labels, file_ids = data["label"].copy(), data["file_id"].copy()
    files = np.unique(file_ids)
    file_scores = np.array([scores[file_ids == item].mean() for item in files])
    file_labels = np.array([labels[file_ids == item][0] for item in files])
    chunk = binary_metrics(labels, scores, runtime.contract.threshold)
    file = binary_metrics(file_labels, file_scores, runtime.contract.threshold)
    matched = (chunk["confusion_matrix"] == [[299, 6], [0, 202]]
               and file["confusion_matrix"] == [[136, 4], [0, 140]]
               and np.isclose(chunk["roc_auc"], 0.9987015094952119, rtol=0, atol=1e-7)
               and np.isclose(file["roc_auc"], 0.9971428571428571, rtol=0, atol=1e-7))
    report = {
        "dataset": "test.npz; split asli, bukan data unggahan atau data training baru",
        "test_npz_sha256": hashlib.sha256(test_path.read_bytes()).hexdigest(),
        "model_sha256": MODEL_SHA256, "metadata_sha256": META_SHA256,
        "model_version": runtime.version, "threshold": runtime.contract.threshold,
        "threshold_operator": ">", "classes": list(runtime.contract.classes),
        "chunk": chunk, "file": file,
        "baseline_reproduced": bool(matched),
        "targets_file_level_pass": bool(file["accuracy"] >= 0.90 and file["f1_fake"] >= 0.90 and file["eer"] <= 0.10),
        "raw_audio_parity": {"status": "unverified", "reason": "Belum ada freeze training dan golden audio mentah Kaggle."},
        "training_performed": False,
        "environment": {
            "python": sys.version.split()[0], "platform": platform.platform(), "cpu": platform.processor(),
            "libraries": {name: importlib.metadata.version(name) for name in ("tensorflow", "keras", "numpy", "scikit-learn", "torch", "torchaudio", "torchcodec", "librosa")},
        },
        "evaluation_seconds": time.perf_counter() - started,
        "score_reference_origin": "Dihasilkan lokal dari model unduhan; bukan vector skor asli Kaggle.",
    }
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output / "local-score-reference.npz", chunk_scores=scores, chunk_labels=labels,
                        file_ids=file_ids, unique_files=files, file_scores=file_scores, file_labels=file_labels)
    (output / "test-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report
