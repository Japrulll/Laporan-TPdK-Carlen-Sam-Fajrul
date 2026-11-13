import streamlit as st
from time import perf_counter


def render_result(result: dict) -> None:
    st.divider()
    st.subheader("Hasil pemeriksaan")
    st.markdown(f"### {result['label']}")
    score, confidence = st.columns(2)
    score.metric("Skor deepfake", f"{result['score_fake'] * 100:.2f}%".replace(".", ","))
    confidence.metric("Keyakinan model", f"{result['confidence'] * 100:.2f}%".replace(".", ","))
    st.caption(
        "Skor deepfake adalah skor kelas fake. Keyakinan model = max(p, 1 − p), "
        "bukan selalu skor kelas yang dipilih. Keduanya belum dikalibrasi dan "
        "bukan jaminan kebenaran hasil."
    )
    threshold = f"{result['threshold']:.6f}".replace(".", ",")
    st.caption(
        f"Ambang klasifikasi: {threshold}. "
        "Label ditetapkan layanan berdasarkan ambang model, bukan aturan 50%."
    )
    coverage = result["analysis"]
    start = f"{coverage['start_seconds']:.6f}".replace(".", ",")
    end = f"{coverage['end_seconds']:.6f}".replace(".", ",")
    duration = f"{result['duration_seconds']:.6f}".replace(".", ",")
    message = (
        f"Rentang yang dianalisis: {start}–{end} detik dari durasi asli {duration} detik "
        f"({coverage['chunk_count']} potongan; kebijakan notebook_max4). "
    )
    if coverage["complete"]:
        st.info(message + "Interpretasikan hasil sesuai rentang ini dan batasan model.")
    else:
        st.warning(message + "Bagian di luar rentang ini tidak dianalisis; hasil tidak mewakili seluruh rekaman.")
    for warning in result["warnings"]:
        st.warning(warning)
    st.caption("Ambang peringatan mutu merupakan usulan engineering terpisah, bukan parameter training; audio model tidak diubah.")
    with st.expander("Rincian dan keterbatasan hasil", expanded=True):
        # Plain text prevents filenames from becoming markup or external assets.
        st.text(f"Berkas: {result['file_name']}")
        st.text(f"Diperiksa (UTC): {result['checked_at']}")
        st.text(f"Versi model: {result['model_version']}")
        st.text(f"SHA-256 audio: {result['sha256']}")
        st.caption(f"Waktu pemrosesan: {result['processing_seconds']:.2f} detik.")
        for limitation in result["limitations"]:
            st.write(limitation)
    st.subheader("Unduh laporan")
    st.caption(
        "JSON memuat data terstruktur; TXT memuat ringkasan yang mudah dibaca. "
        "Keduanya memuat hasil, rentang analisis, dan keterbatasan, bukan audio asli. "
        "Laporan memuat nama berkas; bagikan hanya jika diperlukan."
    )


def render_downloads(result: dict) -> None:
    """Bentuk unduhan di memori tanpa menjalankan ulang inferensi saat diklik."""
    from adadeh.reporting import to_json, to_text

    json_column, text_column = st.columns(2)
    json_column.download_button(
        "Unduh JSON", data=to_json(result), file_name="adadeh-hasil.json",
        mime="application/json", on_click="ignore", width="stretch",
    )
    text_column.download_button(
        "Unduh TXT", data=to_text(result), file_name="adadeh-hasil.txt",
        mime="text/plain; charset=utf-8", on_click="ignore", width="stretch",
    )


def _warm_runtime(runtime) -> None:
    """Siapkan pustaka DSP dan inferensi sebelum unggahan; tidak melatih model."""
    import torch
    from adadeh.preprocessing import extract_features

    synthetic = torch.zeros((1, runtime.contract.chunk_dur), dtype=torch.float32)
    batch = extract_features(synthetic, runtime.contract.global_sr, runtime.contract)
    runtime.predict_raw_features(batch.raw)


@st.cache_resource(show_spinner=False)
def get_runtime():
    """Cache hanya berisi model terverifikasi dan pengunci inferensinya."""
    from adadeh.model import ModelRuntime

    runtime = ModelRuntime.load()
    _warm_runtime(runtime)
    return runtime


def _analyze_audio(payload: bytes, filename: str, runtime, progress):
    from adadeh.service import analyze_audio

    return analyze_audio(payload, filename=filename, runtime=runtime, progress=progress)


def process_upload(uploaded) -> None:
    started = perf_counter()
    if uploaded.size > 100_000_000:
        st.error("Ukuran audio melebihi 100.000.000 byte (100 MB). Pilih berkas yang lebih kecil.")
        return
    from adadeh.audio import AudioValidationError
    from adadeh.model import ModelArtifactError

    with st.status("Memuat model terverifikasi…", expanded=True) as status:
        try:
            runtime = get_runtime()
            status.update(label="Memeriksa audio…")
            result = _analyze_audio(
                uploaded.getvalue(), filename=uploaded.name, runtime=runtime, progress=status.write,
            )
            result = {**result, "processing_seconds": perf_counter() - started}
        except AudioValidationError as exc:
            # Only approved, constant messages may cross the privacy boundary.
            safe_messages = {
                "Durasi audio harus antara 2,5 dan 600 detik.",
                "Ukuran audio melebihi 100.000.000 byte.",
                "Berkas audio kosong.",
            }
            message = str(exc) if str(exc) in safe_messages else (
                "Audio tidak dapat diproses. Periksa isi dan format WAV, FLAC, MP3, M4A, atau OGG; "
                "ekstensi berkas saja tidak menjamin audio valid."
            )
            status.update(label="Audio ditolak", state="error", expanded=False)
            st.error(message)
            return
        except ModelArtifactError:
            status.update(label="Model belum siap", state="error", expanded=False)
            st.error("Model terverifikasi tidak tersedia atau integritasnya tidak sesuai. Hubungi pengelola aplikasi.")
            return
        except Exception:
            status.update(label="Pemeriksaan gagal", state="error", expanded=False)
            st.error("Pemeriksaan tidak dapat diselesaikan. Coba berkas lain atau hubungi pengelola aplikasi.")
            return
        status.update(label="Pemeriksaan selesai", state="complete", expanded=False)
    try:
        render_result(result)
        render_downloads(result)
    except Exception:
        st.error("Hasil atau laporan belum dapat ditampilkan. Hubungi pengelola aplikasi.")


def main() -> None:
    st.set_page_config(page_title="ADADeH · Pemeriksaan audio", page_icon="🎧", layout="centered")
    st.title("ADADeH")
    st.caption("Pemeriksaan indikasi deepfake audio")
    st.info(
        "Hasil merupakan indikator awal, bukan bukti keaslian atau pengganti pemeriksaan "
        "forensik oleh ahli. Jangan menjadikannya satu-satunya dasar keputusan."
    )
    st.warning(
        "Cakupan terbatas mengikuti notebook: hanya maksimal 4 potongan pertama "
        "(hingga 6,25 detik). Bagian setelah rentang tersebut tidak dianalisis."
    )
    with st.expander("Batasan model dan privasi", expanded=False):
        st.markdown(
            "- Model dilatih pada domain audio bahasa Inggris; kinerja untuk bahasa Indonesia "
            "dan kondisi rekaman lain belum dipastikan.\n"
            "- Skor dan keyakinan model belum dikalibrasi; keduanya bukan peluang kebenaran.\n"
            "- Versi lengkap pustaka pada lingkungan pelatihan belum diketahui. Acuan audio mentah "
            "asli dari runtime Kaggle belum tersedia; kesetaraan model diverifikasi pada fitur NPZ.\n"
            "- Audio diproses oleh aplikasi di komputer yang menjalankan server. "
            "Aplikasi tidak menyimpan audio atau hasil secara persisten, dalam cache global, "
            "atau dalam riwayat sesi. Decoder memakai berkas sementara yang dihapus setelah pemrosesan. "
            "Unggahan juga berada sementara dalam memori Streamlit. "
            "Gunakan rekaman yang boleh Anda proses."
        )
    st.subheader("Unggah audio")
    st.caption("WAV, FLAC, MP3, M4A, atau OGG · Maksimal 100 MB (100.000.000 byte). Analisis dimulai otomatis.")
    try:
        with st.spinner("Menyiapkan model dan pipeline sebelum unggahan pertama…"):
            get_runtime()
    except Exception:
        st.error("Model atau pipeline belum siap. Periksa artefak dan instalasi sesuai README; tidak ada prediksi cadangan.")
        return
    uploaded = st.file_uploader("Pilih satu berkas audio", type=["wav", "flac", "mp3", "m4a", "ogg"], accept_multiple_files=False)
    if uploaded is not None:
        process_upload(uploaded)
