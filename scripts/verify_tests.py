"""Run unittest with branch coverage; preserve test exit status and reports."""

import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/verification/coverage"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "COVERAGE_FILE": str(output / ".coverage"),
           "PYTHONPATH": str(root / "src"), "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
    with (output / "tests.log").open("w", encoding="utf-8") as log:
        result = subprocess.run([sys.executable, "-m", "coverage", "run", "-m", "unittest", "discover", "-s", "tests", "-v"],
                                cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
    report = subprocess.run([sys.executable, "-m", "coverage", "json", "-o", str(output / "coverage.json")], cwd=root, env=env)
    with (output / "coverage.txt").open("w", encoding="utf-8") as handle:
        text_report = subprocess.run([sys.executable, "-m", "coverage", "report"], cwd=root, env=env, stdout=handle)
    print(f"Test exit={result.returncode}; reports: {output}")
    return result.returncode or report.returncode or text_report.returncode


if __name__ == "__main__":
    raise SystemExit(main())
