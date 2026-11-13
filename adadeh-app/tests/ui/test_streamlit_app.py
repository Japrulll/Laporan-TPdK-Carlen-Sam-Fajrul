"""UI tests; synthetic results below are test fixtures, never app fallbacks."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.ui


def visible_text(app):
    return "\n".join(
        str(element.value)
        for kind in ("title", "header", "subheader", "markdown", "caption", "info", "warning", "error", "text")
        for element in getattr(app, kind)
    )


def test_initial_render_offers_upload_after_model_preparation(monkeypatch):
    import adadeh.ui as ui
    monkeypatch.setattr(ui, "get_runtime", lambda: object())
    assert (ROOT / "streamlit_app.py").is_file(), "Streamlit entrypoint is missing"
    app = AppTest.from_file(str(ROOT / "streamlit_app.py")).run()
    assert not app.exception
    assert app.title[0].value == "ADADeH"
    text = visible_text(app)
    for phrase in ("indikator awal", "forensik", "seluruh rekaman", "2,5 detik", "bagian akhir",
                   "model dan ambang asli", "belum disetel ulang atau divalidasi ulang",
                   "bahasa Inggris", "NPZ", "100 MB"):
        assert phrase in text
    assert "maksimal 4" not in text
    assert "6,25 detik" not in text
    uploader = app.get("file_uploader")[0]
    assert list(uploader.proto.type) == [".wav", ".flac", ".mp3", ".m4a", ".ogg"]
    assert not app.button
    assert not app.get("download_button")
    assert not app.metric


def test_initial_privacy_notice_discloses_temporary_decoder_files():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=60).run()
    assert not app.exception
    text = visible_text(app)
    assert "berkas sementara" in text
    assert "dihapus" in text
    assert "tidak menulis audio" not in text


def test_local_configuration_disables_telemetry_and_limits_uploads():
    import tomllib

    path = ROOT / ".streamlit" / "config.toml"
    assert path.is_file(), "Private local Streamlit configuration is missing"
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    assert config["browser"]["gatherUsageStats"] is False
    assert config["server"]["headless"] is True
    assert config["server"]["address"] == "127.0.0.1"
    assert config["server"]["maxUploadSize"] == 100
    assert config["client"]["showErrorDetails"] == "none"
    assert config["theme"]["font"] == "sans serif"


@pytest.fixture
def synthetic_result():
    """Explicitly synthetic, for display assertions only; not a model prediction."""
    return {
        "file_name": "contoh-uji.wav", "duration_seconds": 12.345678,
        "checked_at": "2026-11-12T12:00:00+00:00", "sha256": "a" * 64,
        "label": "Terindikasi asli", "predicted_class": "real", "score_fake": 0.505,
        "confidence": 0.505, "threshold": 0.50999,
        "model_version": "model-uji-sintetis", "model_sha256": "b" * 64, "meta_sha256": "c" * 64,
        "analysis": {"chunk_count": 4, "coverage_seconds": 6.25, "start_seconds": 0.0,
                     "end_seconds": 6.25, "policy": "notebook_max4", "complete": False},
        "warnings": ["Peringatan layanan untuk pengujian."],
        "limitations": ["Keterbatasan layanan untuk pengujian."], "processing_seconds": 1.234,
    }


def render_fixture(result):
    from adadeh.ui import render_result
    render_result(result)


def test_result_distinguishes_class_score_confidence_and_actual_coverage(synthetic_result):
    app = AppTest.from_function(render_fixture, args=(synthetic_result,)).run()
    assert not app.exception
    text = visible_text(app)
    for phrase in ("Terindikasi asli", "0,000000–6,250000 detik", "12,345678 detik",
                   "tidak dianalisis", "belum dikalibrasi", "0,509990", "max(p, 1 − p)",
                   "Peringatan layanan", "Keterbatasan layanan", "model-uji-sintetis",
                   "JSON", "TXT"):
        assert phrase in text
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Skor deepfake"] == "50,50%"
    assert metrics["Keyakinan model"] == "50,50%"
    assert not app.button


def test_short_record_still_reports_scope_without_a_blanket_full_record_claim(synthetic_result):
    synthetic_result["duration_seconds"] = 3.75
    synthetic_result["analysis"].update(end_seconds=3.75, coverage_seconds=3.75, complete=True)
    app = AppTest.from_function(render_fixture, args=(synthetic_result,)).run()
    assert not app.exception
    text = visible_text(app)
    assert "0,000000–3,750000 detik" in text
    assert "durasi asli 3,750000 detik" in text
    assert "seluruh durasi rekaman" not in text


def test_upload_triggers_processing_without_an_extra_button(monkeypatch, synthetic_result):
    import io
    import streamlit as st
    import adadeh.ui as ui

    upload = io.BytesIO(b"synthetic-test-only")
    upload.name = "test-only.wav"
    upload.size = len(upload.getvalue())
    processed = []
    runtime = object()

    def synthetic_analyzer(payload, filename, runtime, progress):
        processed.append((payload, filename, runtime))
        progress("Memeriksa audio uji.")
        return synthetic_result

    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: upload)
    monkeypatch.setattr(ui, "get_runtime", lambda: runtime, raising=False)
    monkeypatch.setattr(ui, "_analyze_audio", synthetic_analyzer, raising=False)
    monkeypatch.setattr(ui, "render_downloads", lambda result: None)
    app = AppTest.from_file(str(ROOT / "streamlit_app.py")).run()
    assert not app.exception
    assert processed == [(b"synthetic-test-only", "test-only.wav", runtime)], "Upload must start analysis"
    assert "Terindikasi asli" in visible_text(app)
    assert app.status[0].state == "complete"
    assert not app.button
    assert not app.session_state.filtered_state
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: None)
    app.run()
    assert not app.exception
    assert not app.metric
    assert not app.get("download_button")
    assert len(processed) == 1
    assert not app.session_state.filtered_state


@pytest.mark.parametrize("failure_kind", ["audio", "model", "unexpected"])
def test_processing_errors_are_clear_and_do_not_leak_private_details(monkeypatch, caplog, capsys, failure_kind):
    import io
    import streamlit as st
    import adadeh.ui as ui
    from adadeh.audio import AudioValidationError
    from adadeh.model import ModelArtifactError

    upload = io.BytesIO(b"PRIVATE_AUDIO_BYTES_TEST")
    upload.name = "PRIVATE_FILENAME_TEST.wav"
    upload.size = len(upload.getvalue())
    failures = {
        "audio": AudioValidationError("Durasi audio harus antara 2,5 dan 600 detik."),
        "model": ModelArtifactError("PRIVATE_INTERNAL_PATH_TEST"),
        "unexpected": RuntimeError("PRIVATE_AUDIO_BYTES_TEST PRIVATE_FILENAME_TEST.wav"),
    }

    def fail(*args, **kwargs):
        raise failures[failure_kind]

    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: upload)
    monkeypatch.setattr(ui, "get_runtime", lambda: object())
    monkeypatch.setattr(ui, "_analyze_audio", fail)
    app = AppTest.from_file(str(ROOT / "streamlit_app.py")).run()
    assert not app.exception
    assert app.error
    assert app.status[0].state == "error"
    assert not app.metric
    assert not app.get("download_button")
    if failure_kind == "audio":
        assert "2,5 dan 600 detik" in visible_text(app)
    output = visible_text(app) + caplog.text + str(capsys.readouterr())
    for private in ("PRIVATE_AUDIO_BYTES_TEST", "PRIVATE_FILENAME_TEST", "PRIVATE_INTERNAL_PATH_TEST"):
        assert private not in output


def test_oversized_upload_is_rejected_without_reading_or_reloading_model(monkeypatch):
    import streamlit as st
    import adadeh.ui as ui

    class OversizedUpload:
        name = "private.wav"
        size = 100_000_001

        def getvalue(self):
            raise AssertionError("Oversized audio must not be copied")

    loads = []

    def prepared_model():
        loads.append(True)
        return object()

    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: OversizedUpload())
    monkeypatch.setattr(ui, "get_runtime", prepared_model)
    app = AppTest.from_file(str(ROOT / "streamlit_app.py")).run()
    assert not app.exception
    assert "100.000.000 byte" in app.error[0].value
    assert not app.metric
    assert loads == [True]


def render_export_fixture(result):
    from adadeh.ui import render_downloads
    render_downloads(result)


def test_report_downloads_use_real_serializers_without_rerunning_analysis(synthetic_result, monkeypatch):
    import streamlit as st

    original = st.delta_generator.DeltaGenerator.download_button
    downloads = []

    def record_download(self, *args, **kwargs):
        downloads.append(kwargs)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(st.delta_generator.DeltaGenerator, "download_button", record_download)
    app = AppTest.from_function(render_export_fixture, args=(synthetic_result,)).run()
    assert not app.exception
    from adadeh.reporting import to_json, to_text

    assert [item["data"] for item in downloads] == [to_json(synthetic_result), to_text(synthetic_result)]
    assert [item["file_name"] for item in downloads] == ["adadeh-hasil.json", "adadeh-hasil.txt"]
    assert all(item["on_click"] == "ignore" for item in downloads)
    assert len(app.get("download_button")) == 2


def test_upload_widget_is_available_only_after_runtime_is_ready(monkeypatch):
    import streamlit as st
    import adadeh.ui as ui
    order = []
    monkeypatch.setattr(ui, "get_runtime", lambda: order.append("ready"))
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: order.append("uploader"))
    app = AppTest.from_file(str(ROOT / "streamlit_app.py")).run()
    assert not app.exception
    assert order == ["ready", "uploader"]


def test_pipeline_warmup_does_not_update_original_model_weights():
    import adadeh.ui as ui
    from adadeh.model import ModelRuntime
    import numpy as np
    assert hasattr(ui, "_warm_runtime"), "Pemanasan pipeline sebelum unggah belum tersedia"
    runtime = ModelRuntime.load()
    before = [weight.numpy().copy() for weight in runtime.model.weights]
    assert ui._warm_runtime(runtime) is None
    for expected, actual in zip(before, runtime.model.weights):
        np.testing.assert_array_equal(expected, actual.numpy())


def test_processing_time_includes_model_loading(monkeypatch, synthetic_result):
    import io
    import streamlit as st
    import adadeh.ui as ui

    upload = io.BytesIO(b"synthetic-ui-timing-fixture")
    upload.name = "timing.wav"
    upload.size = len(upload.getvalue())
    ticks = iter([100.0, 107.0])
    displayed = []
    monkeypatch.setattr(ui, "perf_counter", lambda: next(ticks), raising=False)
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: upload)
    monkeypatch.setattr(ui, "get_runtime", lambda: object())
    monkeypatch.setattr(ui, "_analyze_audio", lambda *args, **kwargs: synthetic_result)
    monkeypatch.setattr(ui, "render_result", lambda result: displayed.append(result))
    monkeypatch.setattr(ui, "render_downloads", lambda result: None)
    app = AppTest.from_file(str(ROOT / "streamlit_app.py")).run()
    assert not app.exception
    assert displayed[0]["processing_seconds"] == 7.0


def test_only_model_resource_is_cached(monkeypatch):
    import ast
    from adadeh.model import ModelRuntime
    from adadeh.ui import get_runtime
    import adadeh.ui as ui
    monkeypatch.setattr(ui, "_warm_runtime", lambda runtime: None)

    loaded = []
    runtime = object()

    def load():
        loaded.append(True)
        return runtime

    monkeypatch.setattr(ModelRuntime, "load", load)
    get_runtime.clear()
    try:
        assert get_runtime() is runtime
        assert get_runtime() is runtime
        assert loaded == [True]
    finally:
        get_runtime.clear()
    tree = ast.parse((ROOT / "src/adadeh/ui.py").read_text(encoding="utf-8"))
    caches = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                text = ast.unparse(decorator)
                if "cache" in text:
                    caches.append((node.name, text))
    assert len(caches) == 1
    assert caches[0][0] == "get_runtime"
    assert "cache_resource" in caches[0][1]
    source = ast.unparse(tree)
    assert "session_state" not in source
    assert "st.exception" not in source
