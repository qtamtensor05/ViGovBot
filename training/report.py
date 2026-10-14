from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_report(run_dir: str | Path) -> Path:
    root = Path(run_dir)
    def load(name):
        path = root / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    training, evaluation, parameters = load("training_metrics.json"), load("evaluation_results.json"), load("parameter_report.json")
    lines = [f"# QLoRA experiment report: {root.name}", "", "> Values marked unavailable were not invented.", ""]
    for title, value in (("Training", training), ("Evaluation", evaluation), ("Parameters", parameters)):
        lines.extend([f"## {title}", "", "```json", json.dumps(value, ensure_ascii=False, indent=2) if value else
                      '{"status": "unavailable", "reason": "artifact not generated"}', "```", ""])
    path = root / "summary_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--run_dir", required=True); args = parser.parse_args()
    print(build_report(args.run_dir))


if __name__ == "__main__":
    main()
