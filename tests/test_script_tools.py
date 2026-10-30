import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RoutingArtifactScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = load_script("verify_routing_artifact.py")

    def test_attempt_text_prefers_flat_diagnostic_field(self):
        raw = {"initial_text": "flat", "retry_text": "retry"}

        self.assertEqual(self.script._attempt_text(raw, "initial"), "flat")
        self.assertEqual(self.script._attempt_text(raw, "retry"), "retry")

    def test_attempt_text_supports_legacy_nested_response(self):
        raw = {"initial": {"message": {"content": "nested"}}}

        self.assertEqual(self.script._attempt_text(raw, "initial"), "nested")
        self.assertEqual(self.script._attempt_text(raw, "retry"), "")


class DatasetV3ValidationScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = load_script("validate_dataset_v3.py")

    @staticmethod
    def _row(test_id, code, question, metadata_filters=None):
        return {
            "test_id": test_id,
            "input": {"question": question, "chat_history": [],
                      "metadata_filters": metadata_filters},
            "ground_truth": {
                "expected_route": "rag_search",
                "ground_truth_standalone_query": question,
                "ground_truth_contexts": [
                    f"[Thủ tục: Tách thửa hoặc hợp thửa đất | Mã TTHC: {code} | Mục: TRÌNH TỰ]"
                ],
            },
        }

    def test_duplicate_name_without_code_is_reported_as_candidate(self):
        rows = [self._row("ambiguous", "1.115490", "Cho mình nội dung bước 2."),
                self._row("variant", "1.115201", "Thủ tục khác", {"source_code": "1.115201"})]

        candidates = self.script.ambiguous_identity_candidates(rows)

        self.assertEqual(candidates, [{"test_id": "ambiguous", "target_code": "1.115490",
                                       "same_name_codes": ["1.115201", "1.115490"]}])

    def test_source_code_in_question_or_filter_resolves_candidate(self):
        rows = [self._row("question", "1.115490", "Thủ tục mã 1.115490"),
                self._row("filter", "1.115201", "Thủ tục khác", {"source_code": "1.115201"})]

        self.assertEqual(self.script.ambiguous_identity_candidates(rows), [])


if __name__ == "__main__":
    unittest.main()
