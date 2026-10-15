import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "rag-architecture-review",
    "document-ingestion-validation",
    "retrieval-debugging",
    "rag-evaluation",
    "dataset-validation",
    "chatbot-api-testing",
    "rag-security-review",
    "context-navigation",
    "minimal-diff-development",
    "task-planning",
    "code-change-verification",
    "context-handoff",
    "usage-benchmark",
}
RETIRED = {
    "context-management",
    "repository-navigation",
    "token-budget-optimization",
}


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class AgentSkillTests(unittest.TestCase):
    def test_manifests_ui_and_one_level_discovery_layout(self):
        root = ROOT / ".agents" / "skills"
        discovered = {
            folder.name for folder in root.iterdir() if folder.is_dir() and (folder / "SKILL.md").is_file()
        }
        self.assertTrue(SKILLS.issubset(discovered))
        self.assertTrue(RETIRED.isdisjoint(discovered))
        for name in SKILLS:
            folder = root / name
            text = (folder / "SKILL.md").read_text(encoding="utf-8")
            parts = text.split("---", 2)
            self.assertEqual(len(parts), 3)
            frontmatter = yaml.safe_load(parts[1])
            self.assertEqual(frontmatter, {
                "name": name,
                "description": frontmatter["description"],
            })
            self.assertRegex(name, r"^[a-z0-9-]{1,64}$")
            self.assertLessEqual(len(frontmatter["description"]), 300)
            self.assertIn("Use", frontmatter["description"])
            self.assertNotIn("\\n", parts[2])
            ui = yaml.safe_load((folder / "agents" / "openai.yaml").read_text(encoding="utf-8"))
            self.assertIn(f"${name}", ui["interface"]["default_prompt"])

    def test_routing_descriptions_distinguish_positive_and_negative_prompts(self):
        root = ROOT / ".agents" / "skills"
        descriptions = {}
        for name in SKILLS:
            text = (root / name / "SKILL.md").read_text(encoding="utf-8")
            descriptions[name] = yaml.safe_load(text.split("---", 2)[1])["description"].casefold()

        cases = {
            "context-navigation": ("implementation is unknown", "known one-file edit"),
            "retrieval-debugging": ("chunks are irrelevant", "generation-only"),
            "rag-architecture-review": ("architecture", "narrow bug fix"),
            "usage-benchmark": ("real comparable runs", "synthetic"),
        }
        for name, (positive, negative) in cases.items():
            self.assertIn(positive, descriptions[name])
            self.assertIn(negative, descriptions[name])

        self.assertNotIn("retrieval", descriptions["chatbot-api-testing"])
        self.assertNotIn("architecture", descriptions["dataset-validation"])

    def test_rag_metric_contract_has_required_definitions_and_unavailable_rule(self):
        text = (ROOT / ".agents/skills/rag-evaluation/references/metric-contracts.md").read_text(encoding="utf-8")
        for metric in ("Precision@K =", "Recall@K =", "MRR =", "nDCG@K =", "EM", "BLEU", "ROUGE", "BERTScore"):
            self.assertIn(metric, text)
        self.assertRegex(text, re.compile(r"groundedness|faithfulness", re.IGNORECASE))
        self.assertIn("null", text)
        self.assertIn("Latency", text)

    def test_ingestion_script_valid_and_invalid_records(self):
        module = load_module(ROOT / ".agents/skills/document-ingestion-validation/scripts/validate_ingestion.py")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "chunks.jsonl"
            path.write_text('{"document_id":"d1","text":"A"}\n{"document_id":"d1","text":"A"}\ninvalid\n', encoding="utf-8")
            report = module.validate(path)
        self.assertEqual(report["duplicate_text_records"], 1)
        self.assertEqual(len(report["parse_errors"]), 1)

    def test_dataset_script_detects_cross_split_leakage_and_invalid_json(self):
        module = load_module(ROOT / ".agents/skills/dataset-validation/scripts/validate_dataset.py")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.jsonl"
            path.write_text('{"question":"Q?","split":"train"}\n{"question":" q? ","split":"test"}\ninvalid\n', encoding="utf-8")
            report = module.validate(path)
        self.assertEqual(report["cross_split_leakage_questions"], ["q?"])
        self.assertEqual(len(report["errors"]), 1)

    def test_benchmark_script_preserves_missing_metrics_and_rejects_bad_condition(self):
        module = load_module(ROOT / ".agents/skills/usage-benchmark/scripts/summarize_benchmark.py")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "runs.jsonl"
            rows = [
                {"task_id": "t1", "condition": "baseline", "completed": True, "turns": 3},
                {"task_id": "t1", "condition": "skills", "completed": True, "turns": 2},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            report = module.summarize(path)
            self.assertIsNone(report["skills"]["input_tokens"])
            self.assertEqual(report["skills"]["turns"], 2)
            path.write_text('{"condition":"invented"}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                module.summarize(path)


if __name__ == "__main__":
    unittest.main()
