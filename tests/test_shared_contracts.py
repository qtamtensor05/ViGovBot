import hashlib
import json
import tempfile
import unicodedata
import unittest
from pathlib import Path
from unittest.mock import patch

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


class SharedContractsTests(unittest.TestCase):
    def test_hash_aliases_stream_multiple_blocks(self):
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "large.bin"
            data = b"abc" * 800000
            path.write_bytes(data)
            with patch.object(Path, "read_bytes", side_effect=AssertionError("must stream")):
                for function in (file_hash, helper_hash, sha256_file, sha256):
                    self.assertEqual(function(path), hashlib.sha256(data).hexdigest())
            self.assertIs(helper_hash, file_hash)
            self.assertIs(sha256_file, file_hash)
            self.assertIs(sha256, file_hash)

    def test_unicode_normalization_parity(self):
        expected = "lệ phí strasse hồ_sơ 10 000 đồng"
        for text in ("LỆ PHÍ Straße: hồ_sơ 10.000 đồng!", unicodedata.normalize("NFD", "LỆ PHÍ Straße: hồ_sơ 10.000 đồng!")):
            for function in (normalize_text, normalize_vietnamese, normalize, _normalize):
                self.assertEqual(function(text), expected)

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
