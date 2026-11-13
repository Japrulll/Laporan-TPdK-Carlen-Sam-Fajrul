"""Evaluasi model asli pada test NPZ tanpa training atau penyesuaian threshold."""
from pathlib import Path
import argparse
import json

from adadeh.evaluation import evaluate_artifacts


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=root / "artifacts/kaggle_output")
    parser.add_argument("--output", type=Path, default=root / "artifacts/evaluation")
    args = parser.parse_args()
    report = evaluate_artifacts(args.artifacts, args.output)
    print(json.dumps({key: report[key] for key in ("chunk", "file", "baseline_reproduced", "targets_file_level_pass", "raw_audio_parity")}, ensure_ascii=False, indent=2))
    if not report["baseline_reproduced"]:
        raise SystemExit("Baseline tidak tereproduksi; hentikan integrasi dan periksa artefak/runtime.")


if __name__ == "__main__":
    main()
