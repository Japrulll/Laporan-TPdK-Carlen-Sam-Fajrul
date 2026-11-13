from pathlib import Path
import importlib.util

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_latency_summary_never_hides_a_slow_cold_request_behind_warm_mean():
    script = ROOT / "scripts/benchmark_app.py"
    if not script.is_file():
        pytest.fail("Benchmark layanan belum tersedia", pytrace=False)
    spec = importlib.util.spec_from_file_location("benchmark_app", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cold = {"duration_seconds": 60, "elapsed_seconds": 12.0}
    warm = [{"duration_seconds": 60, "elapsed_seconds": 2.0}, {"duration_seconds": 10, "elapsed_seconds": 3.0}, {"duration_seconds": 600, "elapsed_seconds": 15.0}]
    summary = module.summarize_timings(cold, warm)
    assert summary["cold_within_10_seconds"] is False
    assert summary["warm_within_10_seconds"] is True
    assert summary["all_observed_within_sla"] is False
    assert summary["warm_max_seconds_for_up_to_60_seconds"] == 3.0
