from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import torch


MAX_UPLOAD_BYTES = 100_000_000
# Batas operasional tambahan, bukan parameter notebook atau klaim laporan.
MAX_DECODED_BYTES = 128_000_000
MAX_SAMPLE_RATE = 192_000
MAX_CHANNELS = 8
PROBE_TIMEOUT_SECONDS = 15
ALLOWED_SUFFIXES = {".wav", ".flac", ".mp3", ".m4a", ".ogg"}


class AudioValidationError(ValueError):
    """Unggahan tidak memenuhi batas audio yang dapat diproses."""

def _validate_envelope(payload: bytes, filename: str) -> None:
    """Periksa amplop unggahan sebelum pemeriksaan audio."""
    if not isinstance(payload, bytes):
        raise AudioValidationError("Unggahan harus berupa bytes.")
    if not payload:
        raise AudioValidationError("Berkas audio kosong.")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise AudioValidationError("Ukuran audio melebihi 100.000.000 byte.")
    if not isinstance(filename, str) or Path(filename).suffix.lower() not in ALLOWED_SUFFIXES:
        raise AudioValidationError("Gunakan format WAV, FLAC, MP3, M4A, atau OGG.")
    if Path(filename).suffix.lower() == ".m4a":
        _reject_external_m4a_references(payload)


def _iter_atoms(data: memoryview, start: int, end: int, budget: list[int]):
    """Baca batas atom ISO BMFF tanpa menyalin isi audio; batasi kerumitan."""
    while start < end:
        budget[0] -= 1
        if budget[0] < 0:
            raise AudioValidationError("Metadata audio M4A melebihi batas 10.000 atom.")
        if end - start < 8:
            raise AudioValidationError("Struktur atom audio M4A tidak valid.")
        size = int.from_bytes(data[start : start + 4], "big")
        kind = bytes(data[start + 4 : start + 8])
        header = 8
        if size == 1:
            if end - start < 16:
                raise AudioValidationError("Struktur atom audio M4A tidak valid.")
            size = int.from_bytes(data[start + 8 : start + 16], "big")
            header = 16
        elif size == 0:
            size = end - start
        if size < header or start + size > end:
            raise AudioValidationError("Struktur atom audio M4A tidak valid.")
        yield kind, start + header, start + size
        start += size


def _reject_external_m4a_references(payload: bytes) -> None:
    """Tolak data-reference eksternal sebelum FFmpeg dapat membuka berkas lain."""
    data = memoryview(payload)
    pending = [(0, len(data))]
    budget = [10_000]
    containers = {b"moov", b"trak", b"mdia", b"minf", b"dinf"}
    while pending:
        start, end = pending.pop()
        for kind, body, limit in _iter_atoms(data, start, end, budget):
            if kind in {b"rmra", b"cmov"}:
                raise AudioValidationError("Audio M4A dengan metadata terkompresi/referensi eksternal tidak diizinkan.")
            if kind in containers:
                pending.append((body, limit))
            elif kind == b"dref":
                if limit - body < 8:
                    raise AudioValidationError("Struktur referensi audio M4A tidak valid.")
                for entry, entry_body, entry_end in _iter_atoms(data, body + 8, limit, budget):
                    if (entry != b"url " or entry_end - entry_body != 4
                            or int.from_bytes(data[entry_body:entry_end], "big") != 1):
                        raise AudioValidationError("Audio M4A dengan referensi eksternal tidak diizinkan.")


@dataclass(frozen=True)
class _ProbeResult:
    sample_rate: int
    channels: int
    duration_seconds: float


def _ffmpeg_directory() -> Path:
    return Path(os.environ.get("ADADEH_FFMPEG_DIR") or (
        Path(__file__).resolve().parents[2] / "artifacts/runtime/ffmpeg/bin"
    ))


def _probe_file(path: Path, suffix: str) -> _ProbeResult:
    executable = _ffmpeg_directory() / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
    command = str(executable) if executable.is_file() else shutil.which("ffprobe")
    if not command:
        raise AudioValidationError("ffprobe tidak tersedia; pasang FFmpeg atau atur ADADEH_FFMPEG_DIR.")
    try:
        completed = subprocess.run(
            [command, "-v", "error", "-protocol_whitelist", "file",
             "-format_whitelist", "wav,flac,mp3,mov,ogg", "-show_entries",
             "stream=codec_type,sample_rate,channels,duration:format=format_name,duration",
             "-of", "json", str(path)],
            capture_output=True, check=False, timeout=PROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioValidationError("Pemeriksaan audio melewati batas waktu 15 detik.") from exc
    except OSError as exc:
        raise AudioValidationError("ffprobe tidak dapat dijalankan; periksa instalasi FFmpeg.") from exc
    if completed.returncode:
        raise AudioValidationError("Berkas tidak dapat dibaca sebagai audio yang valid.")
    try:
        metadata = json.loads(completed.stdout)
    except (ValueError, UnicodeError) as exc:
        raise AudioValidationError("Metadata hasil ffprobe tidak valid.") from exc
    formats = set(metadata.get("format", {}).get("format_name", "").split(","))
    expected = {".wav": "wav", ".flac": "flac", ".mp3": "mp3", ".m4a": "mov", ".ogg": "ogg"}
    if expected[suffix] not in formats:
        raise AudioValidationError("Isi audio tidak sesuai dengan format nama berkas.")
    streams = [stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "audio"]
    if len(streams) != 1:
        raise AudioValidationError("Berkas harus memiliki tepat satu aliran audio.")
    stream = streams[0]
    try:
        duration = float(stream.get("duration", metadata.get("format", {}).get("duration", "nan")))
        sample_rate = int(stream["sample_rate"])
        channels = int(stream["channels"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AudioValidationError("Metadata audio tidak lengkap.") from exc
    _validate_resource_limits(_ProbeResult(sample_rate, channels, duration))
    return _ProbeResult(sample_rate, channels, duration)


def _validate_resource_limits(metadata: _ProbeResult) -> None:
    """Tolak perkiraan alokasi besar sebelum meminta seluruh sampel."""
    duration, sample_rate, channels = metadata.duration_seconds, metadata.sample_rate, metadata.channels
    if not 2.5 <= duration <= 600:
        raise AudioValidationError("Durasi audio harus antara 2,5 dan 600 detik.")
    if not 1 <= sample_rate <= MAX_SAMPLE_RATE or not 1 <= channels <= MAX_CHANNELS:
        raise AudioValidationError("Audio melebihi batas sumber daya: 192.000 Hz atau 8 kanal.")
    if duration * sample_rate * channels * 4 > MAX_DECODED_BYTES:
        raise AudioValidationError("Estimasi audio terdekode melebihi 128.000.000 byte.")


def validate_payload(payload: bytes, filename: str) -> None:
    """Validasi hingga dekode nyata; metadata saja tidak membuktikan audio valid.

    Pemanggil yang juga memerlukan sampel cukup memakai ``decode_audio``;
    fungsi tersebut sudah menjalankan seluruh validasi ini.
    """
    decode_audio(payload, filename)


@dataclass(frozen=True)
class DecodedAudio:
    """Sampel CPU float32 (kanal, waktu), tanpa pencampuran atau resampling."""

    samples: torch.Tensor
    sample_rate: int
    duration_seconds: float


_DLL_HANDLES: dict[str, object] = {}


def _configure_ffmpeg() -> None:
    """Pertahankan pegangan DLL selama proses masih memakai TorchCodec."""
    directory = _ffmpeg_directory().resolve()
    if directory.is_dir():
        name = str(directory)
        entries = os.environ.get("PATH", "").split(os.pathsep)
        entries = [entry for entry in entries if os.path.normcase(entry) != os.path.normcase(name)]
        os.environ["PATH"] = os.pathsep.join([name, *entries])
        if os.name == "nt" and name not in _DLL_HANDLES:
            _DLL_HANDLES[name] = os.add_dll_directory(name)


DECODE_TIMEOUT_SECONDS = 45


def _validate_decoded(decoded: DecodedAudio, metadata: _ProbeResult | None = None) -> None:
    """Periksa hasil dekode tanpa mengubah sampel."""
    samples = decoded.samples
    if (samples.ndim != 2 or samples.dtype != torch.float32 or samples.device.type != "cpu"
            or not 1 <= samples.shape[0] <= MAX_CHANNELS or samples.shape[1] == 0
            or not 1 <= decoded.sample_rate <= MAX_SAMPLE_RATE):
        raise AudioValidationError("Bentuk sampel audio terdekode tidak valid.")
    if samples.numel() * samples.element_size() > MAX_DECODED_BYTES:
        raise AudioValidationError("Audio terdekode melebihi 128.000.000 byte.")
    if not torch.isfinite(samples).all():
        raise AudioValidationError("Audio terdekode berisi nilai tidak hingga (NaN/Inf).")
    duration = samples.shape[1] / decoded.sample_rate
    if not 2.5 <= duration <= 600 or decoded.duration_seconds != duration:
        raise AudioValidationError("Durasi audio terdekode harus antara 2,5 dan 600 detik.")
    if metadata and (decoded.sample_rate != metadata.sample_rate or samples.shape[0] != metadata.channels):
        raise AudioValidationError("Metadata audio berubah selama dekode.")


def _decode_worker(input_path: str, output_path: str) -> None:
    """Isolasi decoder native; hanya proses anak membaca bytes unggahan."""
    try:
        _configure_ffmpeg()
        from torchcodec.decoders import AudioDecoder
    except (ImportError, OSError, RuntimeError) as exc:
        raise AudioValidationError(
            "TorchCodec/FFmpeg tidak tersedia; periksa versi pustaka dan ADADEH_FFMPEG_DIR."
        ) from exc

    try:
        decoder = AudioDecoder(Path(input_path).read_bytes())
        metadata = decoder.metadata
        try:
            limits = _ProbeResult(int(metadata.sample_rate), int(metadata.num_channels),
                                  float(metadata.duration_seconds))
        except (TypeError, ValueError) as exc:
            raise AudioValidationError("Metadata decoder audio tidak lengkap.") from exc
        _validate_resource_limits(limits)
        decoded = decoder.get_all_samples()
    except AudioValidationError:
        raise
    except (RuntimeError, ValueError) as exc:
        raise AudioValidationError("TorchCodec tidak dapat mendekode audio yang valid.") from exc
    _validate_decoded(DecodedAudio(decoded.data, decoded.sample_rate, decoded.duration_seconds))
    np.savez(output_path, samples=decoded.data.numpy(),
             sample_rate=decoded.sample_rate, duration_seconds=decoded.duration_seconds)


def decode_audio(payload: bytes, filename: str) -> DecodedAudio:
    """Dekode bytes asli dalam proses berbatas waktu; tidak ada decoder pengganti."""
    _validate_envelope(payload, filename)
    suffix = Path(filename).suffix.lower()
    with tempfile.TemporaryDirectory(prefix="adadeh-", dir=os.environ.get("TMPDIR")) as directory:
        path = Path(directory) / ("upload" + suffix)
        output = Path(directory) / "decoded.npz"
        path.write_bytes(payload)
        metadata = _probe_file(path, suffix)
        try:
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), str(path), str(output)],
                capture_output=True, check=False, timeout=DECODE_TIMEOUT_SECONDS,
                env={**os.environ, "TMPDIR": directory, "TMP": directory, "TEMP": directory,
                     "TORCHINDUCTOR_CACHE_DIR": str(Path(directory) / "torch-cache")},
            )
        except subprocess.TimeoutExpired as exc:
            raise AudioValidationError("Dekode audio melewati batas waktu 45 detik.") from exc
        except OSError as exc:
            raise AudioValidationError("Proses decoder TorchCodec tidak dapat dijalankan.") from exc
        if completed.returncode:
            message = "TorchCodec tidak dapat mendekode audio ini."
            if completed.returncode == 2:
                message = completed.stdout.decode("utf-8", errors="replace").strip()
            raise AudioValidationError(message)
        with np.load(output, allow_pickle=False) as decoded:
            result = DecodedAudio(
                torch.from_numpy(decoded["samples"].copy()),
                int(decoded["sample_rate"]), float(decoded["duration_seconds"]),
            )
        _validate_decoded(result, metadata)
        return result


if __name__ == "__main__":
    try:
        _decode_worker(sys.argv[1], sys.argv[2])
    except AudioValidationError as error:
        print(str(error))
        sys.exit(2)
