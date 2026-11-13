"""Orkestrasi satu unggahan; data audio tidak disimpan di hasil atau cache."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import re
import time
from typing import Callable

from adadeh.model import ModelRuntime, MODEL_SHA256, META_SHA256
from adadeh.prediction import classify_scores
from adadeh.quality import assess_quality, DEFAULT_QUALITY_POLICY


def analyze_audio(payload: bytes, filename: str, runtime: ModelRuntime | None = None,
                  progress: Callable[[str], None] | None = None) -> dict:
    started = time.perf_counter()
    from adadeh.audio import decode_audio
    from adadeh.preprocessing import extract_features

    announce = progress or (lambda stage: None)
    decoded = batch = scores = None
    try:
        announce("Memeriksa format dan durasi audio")
        decoded = decode_audio(payload, filename)
        announce("Menyiapkan model asli")
        active = runtime if runtime is not None else ModelRuntime.load()
        announce("Membentuk maksimal empat potongan awal sesuai notebook")
        batch = extract_features(decoded.samples, decoded.sample_rate, active.contract)
        announce("Memeriksa mutu tanpa mengubah audio model")
        warnings = assess_quality(decoded.samples.numpy(), decoded.sample_rate)
        announce("Menghitung skor dan ringkasan hasil")
        scores = active.predict_raw_features(batch.raw)
        decision = classify_scores(scores, active.contract)
        complete = abs(decoded.duration_seconds - batch.coverage_seconds) <= max(1 / decoded.sample_rate, 1 / active.contract.global_sr)
        if not complete:
            warnings.append("Hanya potongan awal yang dianalisis; bagian rekaman setelah rentang yang ditampilkan tidak dianalisis.")
        safe_name = re.sub(r"[\x00-\x1f\x7f]", "", filename.replace("\\", "/").rsplit("/", 1)[-1])[:240]
        result = {
            "file_name": safe_name, "duration_seconds": float(decoded.duration_seconds),
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            **decision,
            "model_version": active.version, "model_sha256": MODEL_SHA256, "meta_sha256": META_SHA256,
            "analysis": {
                "chunk_count": int(batch.chunk_count), "coverage_seconds": float(batch.coverage_seconds),
                "start_seconds": 0.0, "end_seconds": float(batch.coverage_seconds),
                "policy": "notebook_max4", "complete": bool(complete),
            },
            "warnings": warnings,
            "limitations": [
                "Hasil merupakan indikasi awal, bukan pengganti pemeriksaan forensik digital oleh ahli.",
                "Model dilatih pada satu dataset berbahasa Inggris; generalisasi bahasa Indonesia dan audio dunia nyata belum terbukti.",
                "Skor model belum terkalibrasi dan bukan probabilitas bahwa kesimpulan pasti benar.",
                "Kompatibilitas notebook membatasi analisis pada maksimum empat potongan awal, bukan otomatis seluruh rekaman.",
                "Freeze training dan golden audio mentah belum tersedia; kesetaraan dengan Kaggle baru diuji pada fitur NPZ.",
                "Ambang peringatan mutu adalah usulan engineering terpisah, bukan parameter atau hasil validasi model.",
            ],
            "quality_policy": asdict(DEFAULT_QUALITY_POLICY), "quality_policy_status": "proposed_engineering_defaults",
            "raw_audio_parity": "unverified", "processing_seconds": time.perf_counter() - started,
        }
        return result
    finally:
        decoded = batch = scores = None
        payload = b""
