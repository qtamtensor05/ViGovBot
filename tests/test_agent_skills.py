import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "rag-architecture-review", "document-ingestion-validation", "retrieval-debugging",
    "rag-evaluation", "dataset-validation", "chatbot-api-testing", "rag-security-review",
    "context-management", "token-budget-optimization", "minimal-diff-development",
    "task-planning", "code-change-verification", "context-handoff",
    "repository-navigation", "usage-benchmark",
}


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class AgentSkillTests(unittest.TestCase):
    def test_manifests_and_discovery_layout(self):
        root = ROOT / ".agents" / "skills"
        for name in SKILLS:
            folder = root / name
            text = (folder / "SKILL.md").read_text(encoding="utf-8")
            frontmatter = yaml.safe_load(text.split("---", 2)[1])
            self.assertEqual(frontmatter["name"], name)
            self.assertIn("Use", frontmatter["description"])
            for heading in ("## Hợp đồng", "## Quy trình", "## Ví dụ", "## Giới hạn và kiểm chứng"):
                self.assertIn(heading, text)
            ui = yaml.safe_load((folder / "agents/openai.yaml").read_text(encoding="utf-8"))
            self.assertIn(f"${name}", ui["interface"]["default_prompt"])

    def test_ingestion_script_valid_and_invalid_records(self):
        module = load_module(ROOT / ".agents/skills/document-ingestion-validation/scripts/validate_ingestion.py")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "chunks.jsonl"
            path.write_text('{"document_id":"d1","text":"A"}\n{"document_id":"d1","text":"A"}\ninvalid\n', encoding="utf-8")
            report = module.validate(path)
        self.assertEqual(report["duplicate_text_records"], 1)
        self.assertEqual(len(report["parse_errors"]), 1)

    def test_dataset_script_detects_cross_split_leakage(self):
        module = load_module(ROOT / ".agents/skills/dataset-validation/scripts/validate_dataset.py")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.jsonl"
            path.write_text('{"question":"Q?","split":"train"}\n{"question":" q? ","split":"test"}\n', encoding="utf-8")
            report = module.validate(path)
        self.assertEqual(report["cross_split_leakage_questions"], ["q?"])

    def test_benchmark_script_preserves_missing_metrics(self):
        module = load_module(ROOT / ".agents/skills/usage-benchmark/scripts/summarize_benchmark.py")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "runs.jsonl"
            rows = [{"condition": "baseline", "completed": True, "turns": 3}, {"condition": "skills", "completed": True, "turns": 2}]
            path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            report = module.summarize(path)
        self.assertIsNone(report["skills"]["input_tokens"])
        self.assertEqual(report["skills"]["turns"], 2)


if __name__ == "__main__":
    unittest.main()
