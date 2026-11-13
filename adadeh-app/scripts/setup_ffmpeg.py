"""Unduh FFmpeg shared terpin untuk TorchCodec Windows, bukan saat inferensi."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile

URL = "https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/autobuild-2026-11-12-15-40/ffmpeg-n8.1.3-35-gf1acb0a266-win64-gpl-shared-8.1.zip"
SHA256 = "f4aa246a9a34b592d31af94bdc26d82fabe4c77c00b14acd7e487c6af0c1d9f1"
DEFAULT_TARGET = Path(__file__).resolve().parents[1] / "artifacts" / "runtime" / "ffmpeg"


def verify_extract(archive: Path, expected_sha256: str, target: Path) -> None:
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != expected_sha256:
        raise ValueError("SHA-256 arsip FFmpeg tidak cocok; berkas tidak diekstrak.")
    with zipfile.ZipFile(archive) as source:
        for info in source.infolist():
            parts = PurePosixPath(info.filename).parts
            if ".." in parts or PurePosixPath(info.filename).is_absolute():
                raise ValueError("Path arsip tidak aman.")
        for info in source.infolist():
            parts = PurePosixPath(info.filename).parts
            if info.is_dir():
                continue
            if len(parts) >= 2 and parts[-2] == "bin":
                output = target / "bin" / parts[-1]
            elif parts[-1].lower().startswith(("license", "copying")):
                output = target / parts[-1]
            else:
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            with source.open(info) as src, output.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()
    archive = args.target.parent / "ffmpeg-shared-8.1.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        request = urllib.request.Request(URL, headers={"User-Agent": "adadeh-local-setup"})
        with urllib.request.urlopen(request, timeout=120) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
    verify_extract(archive, SHA256, args.target)
    manifest = {"source_url": URL, "archive_sha256": SHA256, "version": "8.1.3-35-gf1acb0a266", "purpose": "TorchCodec CPU; dependency aplikasi, bukan versi training yang diketahui"}
    (args.target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"FFmpeg shared siap: {args.target / 'bin'}")


if __name__ == "__main__":
    main()
