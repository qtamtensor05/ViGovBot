import json
import tempfile
import unittest
from pathlib import Path


class ReadinessTests(unittest.TestCase):
    def test_readiness_does_not_load_model_or_train(self):
        try:
            import matplotlib  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            self.skipTest("Optional plotting dependencies unavailable")
        from training.readiness import check_readiness
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "readiness.json"
            result = check_readiness("configs/training/environments/rtx5060ti_16gb.yaml", output)
            self.assertEqual(result["status"], "READY")
            self.assertFalse(result["model_weights_loaded"])
            self.assertFalse(result["full_training_started"])
            persisted = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "READY")


if __name__ == "__main__": unittest.main()
