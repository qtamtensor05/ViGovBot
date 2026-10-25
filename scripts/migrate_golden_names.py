"""One-time mechanical import and command-name migration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
replacements = {
    "from .review import fingerprint": "from .provenance import fingerprint",
    "from vigovbot.evaluation.review import fingerprint": "from vigovbot.evaluation.provenance import fingerprint",
    "from .v2 import": "from .records import",
    "vigovbot.evaluation.v2": "vigovbot.evaluation.records",
    "from .offline_v2 import": "from .scoring import",
    "vigovbot.evaluation.offline_v2": "vigovbot.evaluation.scoring",
    "run_v2": "capture_predictions",
    "export_v2": "export_scores",
    "score_offline_v2": "score_supplemental",
    "run-v2": "run",
    "export-v2": "score",
    "score-v2-offline": "score",
    "complete-v2": "evaluate",
    "judge-v2": "score",
    "pairwise-v2": "compare",
}
for folder in ("src", "tests", "scripts"):
    for path in (ROOT / folder).rglob("*.py"):
        if path == Path(__file__).resolve():
            continue
        before = path.read_text(encoding="utf-8")
        after = before
        for old, new in replacements.items():
            after = after.replace(old, new)
        if after != before:
            path.write_text(after, encoding="utf-8")
