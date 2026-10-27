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


if __name__ == "__main__":
    unittest.main()
