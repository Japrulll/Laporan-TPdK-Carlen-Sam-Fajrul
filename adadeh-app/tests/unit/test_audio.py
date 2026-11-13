"""Audio sintetis untuk uji keamanan/decoder, bukan data evaluasi akurasi."""
import io
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import soundfile as sf
import torch

from adadeh.audio import AudioValidationError, decode_audio, validate_payload


def make_wav(duration=3.0, sample_rate=16000, channels=1):
    """Buat WAV sintetis dalam memori; tidak memakai rekaman pengguna."""
    time = np.arange(round(duration * sample_rate)) / sample_rate
    data = 0.25 * np.sin(2 * np.pi * 440 * time)
    if channels > 1:
        data = np.stack([data * (index + 1) / channels for index in range(channels)], axis=1)
    output = io.BytesIO()
    sf.write(output, data, sample_rate, format="WAV", subtype="PCM_16")
    return output.getvalue()


@pytest.mark.parametrize("payload,filename,message", [
    (b"", "empty.wav", "kosong"),
    (b"abc", "file.exe", "format"),
    (b"abc", "file", "format"),
    (bytearray(b"abc"), "file.wav", "bytes"),
    (b"x" * 100_000_001, "file.wav", "100.000.000"),
])
def test_rejects_invalid_upload_envelope(payload, filename, message):
    with pytest.raises(AudioValidationError, match=message):
        validate_payload(payload, filename)


def test_probe_accepts_real_wav_and_removes_uploaded_temporary_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    assert validate_payload(make_wav(), "rekaman.WAV") is None
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("payload,filename", [
    (b"bukan audio", "audio.wav"),
    (b"#EXTM3U\nhttps://example.invalid/private.mp3\n", "audio.mp3"),
    (b"[playlist]\nFile1=file:///etc/passwd\n", "audio.ogg"),
    (make_wav(), "audio.flac"),
])
def test_probe_rejects_corruption_playlists_and_suffix_mismatch(payload, filename, tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    with pytest.raises(AudioValidationError, match="audio|format"):
        validate_payload(payload, filename)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("duration", [2.499, 600.001])
def test_probe_rejects_duration_outside_inclusive_limits(duration):
    with pytest.raises(AudioValidationError, match="2,5.*600"):
        validate_payload(make_wav(duration), "audio.wav")


@pytest.mark.parametrize("sample_rate,channels", [(384000, 1), (16000, 9)])
def test_probe_rejects_excessive_sample_rate_or_channels(sample_rate, channels):
    with pytest.raises(AudioValidationError, match="sumber daya"):
        validate_payload(make_wav(sample_rate=sample_rate, channels=channels), "audio.wav")


def test_probe_rejects_estimated_decoded_memory_before_decoder(monkeypatch):
    metadata = {"format": {"format_name": "wav", "duration": "600"},
                "streams": [{"codec_type": "audio", "sample_rate": "192000", "channels": 8}]}
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(
        a[0], 0, stdout=json.dumps(metadata).encode(), stderr=b""))
    with pytest.raises(AudioValidationError, match="128.000.000"):
        validate_payload(make_wav(), "audio.wav")


@pytest.mark.parametrize("failure,message", [
    (subprocess.TimeoutExpired("ffprobe", 15), "waktu"),
    (FileNotFoundError("ffprobe"), "ffprobe"),
])
def test_probe_failures_have_indonesian_message_and_cleanup(failure, message, tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    def fail(*args, **kwargs):
        assert kwargs["timeout"] == 15
        raise failure
    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(AudioValidationError, match=message):
        validate_payload(make_wav(), "audio.wav")
    assert list(tmp_path.iterdir()) == []


def test_real_decoder_preserves_original_stereo_rate_and_samples(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    payload = make_wav(sample_rate=22050, channels=2)
    expected, sample_rate = sf.read(io.BytesIO(payload), dtype="float32", always_2d=True)
    decoded = decode_audio(payload, "audio.wav")
    assert decoded.samples.shape == (2, 66150)
    assert decoded.samples.dtype == torch.float32
    assert decoded.samples.device.type == "cpu"
    assert decoded.sample_rate == sample_rate == 22050
    assert decoded.duration_seconds == 3.0
    np.testing.assert_array_equal(decoded.samples.numpy(), expected.T)
    assert list(tmp_path.iterdir()) == []


def test_decoder_timeout_stops_worker_and_cleans_upload(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    real_run = subprocess.run
    def expire_worker(command, **kwargs):
        if command[0] == sys.executable:
            assert kwargs["timeout"] == 45
            raise subprocess.TimeoutExpired(command[0], 45)
        return real_run(command, **kwargs)
    monkeypatch.setattr(subprocess, "run", expire_worker)
    with pytest.raises(AudioValidationError, match="waktu.*45"):
        decode_audio(make_wav(), "audio.wav")
    assert list(tmp_path.iterdir()) == []


def test_worker_reports_missing_torchcodec_without_fallback(tmp_path, monkeypatch):
    from adadeh.audio import _decode_worker
    input_path = tmp_path / "audio.wav"
    input_path.write_bytes(make_wav())
    monkeypatch.setitem(sys.modules, "torchcodec.decoders", None)
    with pytest.raises(AudioValidationError, match="TorchCodec/FFmpeg.*ADADEH_FFMPEG_DIR"):
        _decode_worker(str(input_path), str(tmp_path / "decoded.npz"))
    assert not (tmp_path / "decoded.npz").exists()


@pytest.mark.parametrize("invalid", ["duration", "nonfinite", "metadata", "memory"])
def test_rejects_invalid_decoded_result_even_when_probe_looks_valid(invalid, tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    real_run = subprocess.run
    def invalid_worker(command, **kwargs):
        if command[0] != sys.executable:
            return real_run(command, **kwargs)
        data = np.zeros((1, 48000), dtype=np.float32)
        rate, duration = 16000, 3.0
        if invalid == "duration":
            data = data[:, :16000]
            duration = 1.0
        elif invalid == "nonfinite":
            data[0, 0] = np.nan
        elif invalid == "metadata":
            rate = 22050
        elif invalid == "memory":
            monkeypatch.setattr(importlib.import_module("adadeh.audio"), "MAX_DECODED_BYTES", 100)
        np.savez(command[-1], samples=data, sample_rate=rate, duration_seconds=duration)
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")
    monkeypatch.setattr(subprocess, "run", invalid_worker)
    with pytest.raises(AudioValidationError, match="audio|Audio"):
        decode_audio(make_wav(), "audio.wav")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(os.name != "nt", reason="Pengelolaan DLL khusus Windows.")
def test_ffmpeg_directory_moves_to_front_and_dll_handle_is_retained(tmp_path, monkeypatch):
    audio = importlib.import_module("adadeh.audio")
    directory = str(tmp_path.resolve())
    monkeypatch.setenv("ADADEH_FFMPEG_DIR", directory)
    monkeypatch.setenv("PATH", "older-ffmpeg" + os.pathsep + directory)
    monkeypatch.setattr(audio, "_DLL_HANDLES", {})
    handles = []
    def add_directory(path):
        handle = object()
        handles.append(handle)
        return handle
    monkeypatch.setattr(os, "add_dll_directory", add_directory)
    audio._configure_ffmpeg()
    audio._configure_ffmpeg()
    assert os.environ["PATH"].split(os.pathsep)[0] == directory
    assert len(handles) == 1
    assert audio._DLL_HANDLES[directory] is handles[0]


def test_external_m4a_reference_is_rejected_before_probe(monkeypatch):
    def atom(kind, body):
        return (len(body) + 8).to_bytes(4, "big") + kind + body
    reference = atom(b"url ", b"\x00\x00\x00\x00https://example.invalid/private.wav\x00")
    data = atom(b"dref", b"\x00\x00\x00\x00\x00\x00\x00\x01" + reference)
    for kind in [b"dinf", b"minf", b"mdia", b"trak", b"moov"]:
        data = atom(kind, data)
    def forbidden_probe(*args, **kwargs):
        pytest.fail("Referensi eksternal tidak boleh mencapai FFmpeg.")
    monkeypatch.setattr(subprocess, "run", forbidden_probe)
    with pytest.raises(AudioValidationError, match="referensi eksternal"):
        validate_payload(data, "audio.m4a")


@pytest.mark.parametrize("kind", [b"rmra", b"cmov"])
def test_m4a_indirect_or_compressed_metadata_never_reaches_probe(kind, monkeypatch):
    data = (8).to_bytes(4, "big") + kind
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("Atom berisiko mencapai probe."))
    with pytest.raises(AudioValidationError, match="metadata|referensi eksternal"):
        validate_payload(data, "audio.m4a")


def test_m4a_excessive_atom_count_never_reaches_probe(monkeypatch):
    data = ((8).to_bytes(4, "big") + b"free") * 10001
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("Terlalu banyak atom mencapai probe."))
    with pytest.raises(AudioValidationError, match="10.000 atom"):
        validate_payload(data, "audio.m4a")


def test_worker_checks_its_own_metadata_before_allocating_samples(tmp_path, monkeypatch):
    from types import SimpleNamespace
    audio = importlib.import_module("adadeh.audio")
    source = tmp_path / "audio.wav"
    source.write_bytes(make_wav())
    class OversizedDecoder:
        def __init__(self, payload):
            assert isinstance(payload, bytes)
            self.metadata = SimpleNamespace(sample_rate=192000, num_channels=8, duration_seconds=600.0)
        def get_all_samples(self):
            pytest.fail("Dekoder tidak boleh mengalokasikan sampel yang melebihi batas.")
    monkeypatch.setitem(sys.modules, "torchcodec.decoders", SimpleNamespace(AudioDecoder=OversizedDecoder))
    with pytest.raises(AudioValidationError, match="128.000.000"):
        audio._decode_worker(str(source), str(tmp_path / "decoded.npz"))


def test_validation_rejects_flac_header_without_any_audio_frames(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    output = io.BytesIO()
    sf.write(output, np.zeros(48000), 16000, format="FLAC")
    payload = output.getvalue()
    cursor = 4
    while True:
        flag = payload[cursor]
        length = int.from_bytes(payload[cursor + 1 : cursor + 4], "big")
        cursor += 4 + length
        if flag & 128:
            break
    with pytest.raises(AudioValidationError, match="audio"):
        validate_payload(payload[:cursor], "header-only.flac")
    assert list(tmp_path.iterdir()) == []


def test_decoder_launch_failure_has_indonesian_error_and_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    real_run = subprocess.run
    def missing_worker(command, **kwargs):
        if command[0] == sys.executable:
            raise OSError("proses tidak tersedia")
        return real_run(command, **kwargs)
    monkeypatch.setattr(subprocess, "run", missing_worker)
    with pytest.raises(AudioValidationError, match="Proses decoder"):
        decode_audio(make_wav(), "audio.wav")
    assert list(tmp_path.iterdir()) == []


def test_probe_invalid_json_has_indonesian_error(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(
        a[0], 0, stdout=b"not-json", stderr=b""))
    with pytest.raises(AudioValidationError, match="Metadata.*valid"):
        validate_payload(make_wav(), "audio.wav")
