from pathlib import Path
import hashlib
import importlib.util
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_ffmpeg_archive_is_verified_before_extracting_only_runtime_files(tmp_path):
    script = ROOT / "scripts" / "setup_ffmpeg.py"
    if not script.is_file():
        pytest.fail("Penyiapan FFmpeg shared belum tersedia", pytrace=False)
    spec = importlib.util.spec_from_file_location("setup_ffmpeg", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("build/bin/avcodec-62.dll", b"synthetic test fixture")
        output.writestr("build/bin/ffprobe.exe", b"synthetic executable fixture")
        output.writestr("build/LICENSE.txt", "license fixture")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="SHA-256"):
        module.verify_extract(archive, "0" * 64, tmp_path / "wrong")
    assert not (tmp_path / "wrong").exists()
    module.verify_extract(archive, digest, tmp_path / "runtime")
    assert (tmp_path / "runtime/bin/avcodec-62.dll").read_bytes() == b"synthetic test fixture"
    assert (tmp_path / "runtime/LICENSE.txt").exists()
