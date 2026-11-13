"""Ringkasan unduhan; tidak menyimpan audio atau mencatatnya ke log."""
import json

REQUIRED_FIELDS = ("file_name", "duration_seconds", "checked_at", "sha256", "label", "score_fake", "model_version", "limitations")


def _validate(result: dict) -> None:
    if any(name not in result for name in REQUIRED_FIELDS):
        raise ValueError("Ringkasan tidak memuat seluruh informasi wajib.")


def to_json(result: dict) -> bytes:
    _validate(result)
    return json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


def to_text(result: dict) -> bytes:
    _validate(result)
    number = lambda value: f"{value:.2f}".replace(".", ",")
    analysis = result["analysis"]
    lines = [
        "ADADeH — Ringkasan pemeriksaan indikasi deepfake audio",
        f"Nama berkas: {result['file_name']}",
        f"Durasi rekaman: {number(result['duration_seconds'])} detik",
        f"Waktu pemeriksaan (UTC): {result['checked_at']}",
        f"SHA-256 byte berkas asli: {result['sha256']}",
        f"Hasil: {result['label']}",
        f"Skor deepfake: {number(result['score_fake'] * 100)}%",
        f"Skor keyakinan model (belum terkalibrasi): {number(result['confidence'] * 100)}%",
        f"Versi model: {result['model_version']}",
        f"Cakupan: {number(analysis['start_seconds'])}–{number(analysis['end_seconds'])} detik; {analysis['chunk_count']} potongan awal",
        "Kebijakan: kompatibilitas notebook, maksimum empat potongan; bukan analisis otomatis seluruh rekaman.",
        "", "Peringatan mutu/cakupan:",
        *[f"- {text}" for text in result.get("warnings", [])],
        "", "Keterangan batasan:",
        *[f"- {text}" for text in result["limitations"]],
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")
