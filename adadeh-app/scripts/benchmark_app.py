"""Benchmark CPU dengan audio sintetis; bukan pengukuran akurasi model."""
from pathlib import Path
import argparse
import json
import os
import platform
import shutil
import subprocess
import time

import numpy as np
import psutil
import soundfile as sf

from adadeh.model import ModelRuntime
from adadeh.service import analyze_audio


def summarize_timings(cold: dict, warm: list[dict]) -> dict:
    eligible = [row["elapsed_seconds"] for row in warm if row["duration_seconds"] <= 60]
    cold_pass = cold["duration_seconds"] > 60 or cold["elapsed_seconds"] <= 10
    warm_pass = all(value <= 10 for value in eligible)
    return {
        "cold_within_10_seconds": bool(cold_pass),
        "warm_within_10_seconds": bool(warm_pass),
        "all_observed_within_sla": bool(cold_pass and warm_pass),
        "warm_max_seconds_for_up_to_60_seconds": max(eligible, default=None),
        "scope": "observasi proses layanan pada hardware ini; bukan bukti seluruh perangkat/browser",
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--include-long", action="store_true")
    parser.add_argument("--output", type=Path, default=root / "artifacts/benchmark")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("Jumlah pengulangan harus positif.")
    args.output.mkdir(parents=True, exist_ok=True)
    temporary = args.output / "temporary"
    temporary.mkdir(exist_ok=True)
    os.environ["TMPDIR"] = str(temporary.resolve())
    fixtures = args.output / "synthetic-fixtures"
    fixtures.mkdir(exist_ok=True)

    def make_wave(name, duration, rate=16000, channels=1):
        target = fixtures / name
        signal = (0.2 * np.sin(2 * np.pi * 440 * np.arange(int(duration * rate), dtype=np.float32) / rate))
        if channels > 1:
            signal = np.stack([signal] * channels, axis=1)
        sf.write(target, signal, rate, subtype="PCM_16")
        return target

    short = make_wave("synthetic-2.5s.wav", 2.5)
    medium = make_wave("synthetic-10s.wav", 10)
    minute = make_wave("synthetic-60s.wav", 60)
    stereo = make_wave("synthetic-stereo-44100-60s.wav", 60, 44100, 2)
    compressed_source = make_wave("synthetic-compressed-source-59s.wav", 59)
    executable = root / "artifacts/runtime/ffmpeg/bin/ffmpeg.exe"
    ffmpeg = str(executable) if executable.is_file() else shutil.which("ffmpeg")
    cases = [short, medium, minute, stereo]
    for extension, codec in (("flac", "flac"), ("mp3", "libmp3lame"), ("m4a", "aac"), ("ogg", "libvorbis")):
        target = fixtures / f"synthetic-59s.{extension}"
        completed = subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(compressed_source), "-c:a", codec, str(target)], capture_output=True, timeout=60)
        if completed.returncode:
            raise RuntimeError(f"Pembuatan fixture sintetis {extension} gagal.")
        cases.append(target)
    if args.include_long:
        cases.append(make_wave("synthetic-600s.wav", 600))

    def measure(path, runtime=None):
        payload = path.read_bytes()
        started = time.perf_counter()
        result = analyze_audio(payload, path.name, runtime=runtime)
        return {"fixture": path.name, "bytes": len(payload), "duration_seconds": result["duration_seconds"],
                "elapsed_seconds": time.perf_counter() - started,
                "chunk_count": result["analysis"]["chunk_count"], "coverage_seconds": result["analysis"]["coverage_seconds"]}

    cold = measure(minute)
    print("COLD", json.dumps(cold), flush=True)
    runtime = ModelRuntime.load()
    rows = []
    for path in cases:
        for repeat in range(args.repeats):
            row = measure(path, runtime)
            row["repeat"] = repeat + 1
            rows.append(row)
            print("WARM", json.dumps(row), flush=True)
    memory = psutil.Process().memory_info()
    report = {"purpose": "audio sintetis untuk uji waktu dan alur; tidak mengukur akurasi",
              "cold": cold, "warm": rows, "summary": summarize_timings(cold, rows),
              "hardware": {"platform": platform.platform(), "processor": platform.processor(),
                           "logical_cpus": psutil.cpu_count(), "physical_memory_bytes": psutil.virtual_memory().total,
                           "parent_rss_end_bytes": memory.rss, "peak_parent_working_set_bytes": getattr(memory, "peak_wset", None),
                           "memory_scope": "hanya parent; bukan peak gabungan parent dan decoder anak"}}
    (args.output / "benchmark-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
