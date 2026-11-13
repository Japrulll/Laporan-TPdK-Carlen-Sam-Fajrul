"""Uji Chrome headless terisolasi: unggah nyata, unduh, mobile, dan input rusak."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import time
from urllib.parse import urlparse

import numpy as np
from playwright.sync_api import sync_playwright


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--output", type=Path, default=root / "artifacts/qa")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    temp = args.output / "browser-temp"
    temp.mkdir(exist_ok=True)
    for key in ("TMPDIR", "TEMP", "TMP"):
        os.environ[key] = str(temp.resolve())
    candidates = [Path("C:/Program Files/Google/Chrome/Application/chrome.exe"), Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")]
    executable = next((path for path in candidates if path.is_file()), None)
    if executable is None:
        raise SystemExit("Chrome/Edge lokal tidak ditemukan; uji browser belum dilakukan.")
    fixture = root / "artifacts/reference_audio/file-40.flac"
    with np.load(root / "artifacts/evaluation/local-score-reference.npz", allow_pickle=False) as data:
        index = int(np.flatnonzero(data["unique_files"] == 40)[0])
        expected_score = float(data["file_scores"][index])
    expected_label = "Terindikasi deepfake" if expected_score > 0.5099999999999999 else "Terindikasi asli"
    page_errors, console_errors, external = [], [], set()
    target_host = urlparse(args.url).netloc
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(executable), headless=True, args=["--disable-background-networking"])
        context = browser.new_context(viewport={"width": 1280, "height": 1000}, accept_downloads=True)
        page = context.new_page()
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("request", lambda request: external.add(request.url) if request.url.startswith(("https://", "http://", "ws://", "wss://")) and urlparse(request.url).netloc != target_host else None)
        initial = time.perf_counter()
        page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        uploader = page.locator('input[type="file"]')
        uploader.wait_for(state="attached", timeout=90000)
        initialization_seconds = time.perf_counter() - initial
        page.screenshot(path=str(args.output / "desktop-ready.png"), full_page=True)
        started = time.perf_counter()
        uploader.set_input_files(str(fixture))
        page.get_by_role("heading", name=expected_label, exact=True).wait_for(timeout=90000)
        browser_result_seconds = time.perf_counter() - started
        page.get_by_role("button", name="Unduh JSON", exact=True).wait_for(timeout=15000)
        with page.expect_download() as event:
            page.get_by_role("button", name="Unduh JSON", exact=True).click()
        json_download = args.output / "browser-result.json"
        event.value.save_as(str(json_download))
        result = json.loads(json_download.read_text(encoding="utf-8"))
        assert result["file_name"] == fixture.name
        assert result["sha256"] == hashlib.sha256(fixture.read_bytes()).hexdigest()
        assert result["label"] == expected_label
        assert abs(result["score_fake"] - expected_score) <= 1e-5
        assert result["analysis"]["chunk_count"] == 4
        assert result["analysis"]["end_seconds"] == 6.25
        assert result["analysis"]["complete"] is False
        with page.expect_download() as event:
            page.get_by_role("button", name="Unduh TXT", exact=True).click()
        event.value.save_as(str(args.output / "browser-result.txt"))
        assert "6,25" in (args.output / "browser-result.txt").read_text(encoding="utf-8")
        page.screenshot(path=str(args.output / "desktop-result.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(600)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(args.output / "mobile-result.png"), full_page=True)
        uploader.set_input_files({"name": "synthetic-invalid.wav", "mimeType": "audio/wav", "buffer": b"synthetic invalid audio fixture, not a valid waveform"})
        page.get_by_text(re.compile("Audio tidak dapat diproses")).wait_for(timeout=30000)
        assert page.get_by_test_id("stMetric").count() == 0
        page.screenshot(path=str(args.output / "invalid-input.png"), full_page=True)
        browser_version = browser.version
        context.close()
        browser.close()
    assert not page_errors, page_errors
    assert not console_errors, console_errors
    assert not external, sorted(external)
    report = {"status": "PASS", "browser": browser_version, "isolated_headless_profile": True,
              "existing_user_browser_closed": False, "fixture": fixture.name,
              "initialization_before_upload_seconds": initialization_seconds,
              "upload_to_visible_result_seconds": browser_result_seconds,
              "backend_reported_seconds": result["processing_seconds"],
              "expected_score_from_original_npz": expected_score, "actual_browser_score": result["score_fake"],
              "tested": ["real FLAC upload", "actual model prediction", "JSON download", "TXT download", "390px viewport", "corrupt WAV rejection", "no stale result after error"],
              "page_errors": page_errors, "console_errors": console_errors, "external_requests": sorted(external),
              "not_tested": ["Safari", "Firefox", "native physical mobile device", "public TLS deployment", "user comprehension study"]}
    (args.output / "browser-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
