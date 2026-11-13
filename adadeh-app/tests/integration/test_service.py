from importlib import import_module
import hashlib
import io

import numpy as np
import pytest
import soundfile as sf


def test_real_service_returns_actual_scores_provenance_and_capped_coverage():
    try:
        service = import_module("adadeh.service")
    except ModuleNotFoundError:
        pytest.fail("Layanan inferensi belum tersedia", pytrace=False)
    from adadeh.model import ModelRuntime
    from adadeh.audio import decode_audio
    from adadeh.preprocessing import extract_features
    runtime = ModelRuntime.load()
    t = np.arange(160000, dtype=np.float32) / 16000
    signal = 0.2 * np.sin(2 * np.pi * 440 * t)
    buffer = io.BytesIO()
    sf.write(buffer, signal, 16000, format="WAV", subtype="PCM_16")
    payload = buffer.getvalue()
    stages = []
    weights = [v.numpy().copy() for v in runtime.model.weights]
    result = service.analyze_audio(payload, r"C:\private\synthetic-test.wav", runtime, stages.append)
    assert result["file_name"] == "synthetic-test.wav"
    assert result["sha256"] == hashlib.sha256(payload).hexdigest()
    assert result["duration_seconds"] == 10.0
    assert result["analysis"]["chunk_count"] == 4
    assert result["analysis"]["end_seconds"] == 6.25
    assert result["analysis"]["complete"] is False
    assert result["model_version"] == runtime.version
    assert result["raw_audio_parity"] == "unverified"
    assert stages and result["limitations"]
    decoded = decode_audio(payload, "synthetic-test.wav")
    batch = extract_features(decoded.samples, decoded.sample_rate, runtime.contract)
    expected = float(runtime.predict_raw_features(batch.raw).mean())
    assert result["score_fake"] == pytest.approx(expected, abs=1e-6)
    for before, after in zip(weights, runtime.model.weights):
        np.testing.assert_array_equal(before, after.numpy())
    from adadeh.reporting import to_json, to_text
    assert to_json(result) and to_text(result)


def test_service_decodes_each_upload_once(monkeypatch):
    from adadeh import audio, service
    from adadeh.model import ModelRuntime
    buffer = io.BytesIO()
    sf.write(buffer, np.zeros(40000, dtype=np.float32), 16000, format="WAV")
    actual_decode = audio.decode_audio
    calls = []

    def traced_decode(payload, filename):
        calls.append(filename)
        return actual_decode(payload, filename)

    monkeypatch.setattr(audio, "decode_audio", traced_decode)
    service.analyze_audio(buffer.getvalue(), "synthetic-single-pass.wav", ModelRuntime.load())
    assert calls == ["synthetic-single-pass.wav"]


def test_invalid_upload_is_rejected_before_loading_model():
    service = import_module("adadeh.service")
    with pytest.raises(ValueError):
        service.analyze_audio(b"", "empty.wav")
