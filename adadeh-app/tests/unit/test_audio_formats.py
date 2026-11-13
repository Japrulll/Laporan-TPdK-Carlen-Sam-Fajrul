"""Fixture sintetis lima format; paritas decoder hanya untuk runtime saat ini."""
import io
import os
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest
import soundfile as sf
import torch

from adadeh.audio import decode_audio, _configure_ffmpeg


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.integration
@pytest.mark.parametrize("suffix,codec", [
    ("wav", "pcm_s16le"), ("flac", "flac"), ("mp3", "libmp3lame"),
    ("m4a", "aac"), ("ogg", "libvorbis"),
])
def test_real_five_formats_match_direct_torchcodec_bytes(suffix, codec, tmp_path, monkeypatch):
    """Tidak membandingkan terhadap audio emas atau freeze pelatihan yang tidak tersedia."""
    sample_rate = 48000
    time = np.arange(150000, dtype=np.float32) / sample_rate
    original = np.stack((0.17 * np.sin(2 * np.pi * 510 * time),
                         0.28 * np.cos(2 * np.pi * 791 * time)), axis=1)
    source = tmp_path / "source.wav"
    sf.write(source, original, sample_rate, subtype="PCM_16")
    target = tmp_path / ("fixture." + suffix)
    executable = ROOT / "artifacts/runtime/ffmpeg/bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    command = str(executable) if executable.is_file() else shutil.which("ffmpeg")
    assert command, "FFmpeg diperlukan untuk menghasilkan fixture sintetis."
    subprocess.run([command, "-nostdin", "-v", "error", "-y", "-i", str(source),
                    "-c:a", codec, str(target)], check=True, capture_output=True, timeout=30)
    payload = target.read_bytes()
    _configure_ffmpeg()
    from torchcodec.decoders import AudioDecoder

    expected = AudioDecoder(payload).get_all_samples()
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setenv("TMPDIR", str(uploads))
    decoded = decode_audio(payload, "fixture." + suffix)
    assert decoded.samples.dtype == torch.float32
    assert decoded.samples.device.type == "cpu"
    assert decoded.samples.shape[0] == 2
    assert decoded.sample_rate == expected.sample_rate == sample_rate
    assert decoded.duration_seconds == expected.duration_seconds
    torch.testing.assert_close(decoded.samples, expected.data, rtol=0, atol=0)
    assert list(uploads.iterdir()) == []


@pytest.mark.integration
@pytest.mark.parametrize("duration", [2.5, 600.0])
def test_mp3_accepts_inclusive_decoded_duration_despite_codec_padding(duration, tmp_path, monkeypatch):
    executable = ROOT / "artifacts/runtime/ffmpeg/bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    command = str(executable) if executable.is_file() else shutil.which("ffmpeg")
    assert command, "FFmpeg diperlukan untuk menghasilkan fixture sintetis."
    target = tmp_path / "boundary.mp3"
    subprocess.run([command, "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=16000:cl=mono", "-t", str(duration), "-c:a", "libmp3lame",
                    str(target)], check=True, capture_output=True, timeout=30)
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setenv("TMPDIR", str(uploads))
    decoded = decode_audio(target.read_bytes(), target.name)
    assert decoded.duration_seconds == duration
    assert list(uploads.iterdir()) == []
