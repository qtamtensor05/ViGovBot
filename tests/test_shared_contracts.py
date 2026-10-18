from tests.dependencies import skip_missing_dependency, requires_dependencies

import hashlib
import json
import tempfile
import unicodedata
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from vigovbot.artifacts import file_hash
    from vigovbot.evaluation.audit import sha256
    from vigovbot.evaluation.io import read_jsonl
    from vigovbot.evaluation.lexical import bleu_metric
    from vigovbot.evaluation.scoring import normalize
    from vigovbot.evaluation.v2 import _normalize
    from vigovbot.experiments import read_results
    from vigovbot.training.data import normalize_text, sha256_file, read_jsonl as training_read
    from vigovbot.training.metrics import normalize_vietnamese, generation_metrics, aggregate_generation_metrics
    from vigovbot.utils.helpers import file_hash as helper_hash
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


class SharedContractsTests(unittest.TestCase):
    @requires_dependencies("sacrebleu", "rouge_score")
    def test_baseline_bleu_uses_shared_backend_with_report_scale(self):
        from vigovbot.evaluation.metrics import bleu_score, METRIC_CONTRACT_VERSION
        self.assertEqual(METRIC_CONTRACT_VERSION, "baseline-vi-lexical-v3")
        for prediction, reference in [("LỆ PHÍ!", "lệ phí"), ("hồ sơ mới", "hồ sơ đủ"), ("", "hồ sơ")]:
            expected = generation_metrics(prediction, reference)["bleu"] / 100
            self.assertAlmostEqual(bleu_score(prediction, reference), expected)

    def test_jsonl_file_zip_and_scoring_share_parser(self):
        import zipfile
        from vigovbot.evaluation.dataset import load_cases
        from vigovbot.evaluation.scoring import read
        from vigovbot.utils.jsonl import iter_jsonl_stream
        row = {"id": "a", "question": {"text": "hồ sơ?", "type": "fact", "difficulty": "easy"},
               "ground_truth": {"answer": "đủ"}}
        content = "\ufeff" + json.dumps(row, ensure_ascii=False) + "\n\n"
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "dataset.jsonl"
            path.write_text(content, encoding="utf-8")
            archive = Path(work) / "data.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("qa_test/dataset.jsonl", content.encode("utf-8"))
            self.assertEqual(load_cases(dataset_path=path), [row])
            self.assertEqual(load_cases(dataset_zip=archive), [row])
            self.assertEqual(read(path), [row])
        with self.assertRaisesRegex(ValueError, "stream:3: invalid JSON"):
            list(iter_jsonl_stream(["{}\n", "\n", "bad"], source="stream", blank_lines="skip"))
        with self.assertRaisesRegex(ValueError, "blank_lines must"):
            list(iter_jsonl_stream([], source="stream", blank_lines="other"))

    def test_hash_aliases_stream_multiple_blocks(self):
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "large.bin"
            data = b"abc" * 800000
            path.write_bytes(data)
            with patch.object(Path, "read_bytes", side_effect=AssertionError("must stream")):
                from vigovbot.evaluation.v2 import _sha256
                self.assertIs(_sha256, file_hash)
                for function in (file_hash, helper_hash, sha256_file, sha256, _sha256):
                    self.assertEqual(function(path), hashlib.sha256(data).hexdigest())
            self.assertIs(helper_hash, file_hash)
            self.assertIs(sha256_file, file_hash)
            self.assertIs(sha256, file_hash)

    @requires_dependencies("rouge_score")
    def test_unicode_normalization_parity(self):
        expected = "lệ phí strasse hồ_sơ 10 000 đồng"
        for text in ("LỆ PHÍ Straße: hồ_sơ 10.000 đồng!", unicodedata.normalize("NFD", "LỆ PHÍ Straße: hồ_sơ 10.000 đồng!")):
            from vigovbot.evaluation.metrics import normalize_answer, rouge_scores
            for function in (normalize_text, normalize_vietnamese, normalize, _normalize, normalize_answer):
                self.assertEqual(function(text), expected)
            self.assertAlmostEqual(rouge_scores(text, expected)["rougeL_f1"], 1.0)

    @requires_dependencies("sacrebleu", "rouge_score")
    def test_training_bleu_matches_modern_contract(self):
        pairs = [("Lệ phí!", "lệ phí"), ("Hồ sơ mới đầy đủ", "hồ sơ đầy đủ")]
        rows = [{"prediction": p, "reference": r, "metrics": generation_metrics(p, r)} for p, r in pairs]
        metric = bleu_metric()
        expected = metric.corpus_score([normalize(p) for p, _ in pairs], [[normalize(r) for _, r in pairs]]).score
        self.assertAlmostEqual(aggregate_generation_metrics(rows)["bleu"], expected)
        self.assertAlmostEqual(rows[0]["metrics"]["bleu"], 100.0)
        self.assertAlmostEqual(rows[0]["metrics"]["rouge_l"], 1.0)

    def test_jsonl_blank_policy_and_recovery_boundaries(self):
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "records.jsonl"
            record = {"id": "x", "messages": [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]}
            valid = json.dumps(record).encode() + b"\n"
            path.write_bytes(valid + b"\n")
            self.assertEqual(list(read_jsonl(path)), [record])
            with self.assertRaisesRegex(ValueError, ":2: blank"):
                training_read(path)
            self.assertEqual(read_results(path, repair_tail=True), [record])
            self.assertEqual(path.read_bytes(), valid + b"\n")
            path.write_bytes(valid + b'{"broken":')
            with self.assertRaises(ValueError):
                list(read_jsonl(path))
            self.assertEqual(path.read_bytes(), valid + b'{"broken":')
            self.assertEqual(read_results(path, repair_tail=True), [record])
            self.assertEqual(path.read_bytes(), valid)
            path.write_bytes(valid + b"broken\n" + valid)
            with self.assertRaises(ValueError):
                read_results(path, repair_tail=True)
            self.assertEqual(path.read_bytes(), valid + b"broken\n" + valid)
