import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from training.artifacts import create_run_dir
from training.control import QLoRAControlCallback


class ArtifactSafetyTests(unittest.TestCase):
    def test_run_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = {"_project_root": str(root), "data": {"output_dir": "outputs"}}
            first = create_run_dir(config, "fixed")
            self.assertTrue(first.is_dir())
            self.assertEqual(
                {"logs", "checkpoints", "best_adapter", "metrics", "predictions", "plots", "reports"},
                {path.name for path in first.iterdir() if path.is_dir()},
            )
            with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                create_run_dir(config, "fixed")


class ControlCallbackTests(unittest.TestCase):
    def test_live_status_tensorboard_metrics_and_graceful_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            callback = QLoRAControlCallback(root)
            callback.started -= 10
            callback.writer = MagicMock()
            state = SimpleNamespace(global_step=7, max_steps=100, epoch=0.2)
            control = SimpleNamespace(should_save=False, should_training_stop=False)
            with patch.object(callback, "_gpu", return_value={"gpu_allocated_bytes": 123}):
                callback.on_log(
                    None,
                    state,
                    control,
                    {"loss": 1.5, "eval_loss": 1.7, "learning_rate": 2e-4, "grad_norm": 0.8},
                )
            live = json.loads((root / "live_status.json").read_text(encoding="utf-8"))
            self.assertEqual(json.loads((root / "state.json").read_text(encoding="utf-8")), live)
            self.assertEqual(live["global_step"], 7)
            self.assertEqual(live["loss"], 1.5)
            self.assertEqual(live["best_validation_loss"], 1.7)
            self.assertGreater(live["eta_seconds"], 0)
            event = json.loads((root / "logs" / "training_events.jsonl").read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(event["global_step"], 7)
            self.assertEqual(event["loss"], 1.5)
            self.assertIn("timestamp_utc", event)
            self.assertEqual(event["gpu_allocated_bytes"], 123)
            (root / "control").mkdir(exist_ok=True)
            (root / "control" / "stop.requested").write_text("stop", encoding="utf-8")
            callback.on_step_end(None, state, control)
            self.assertTrue(control.should_save)
            self.assertTrue(control.should_training_stop)
            ack = json.loads((root / "control" / "stop.acknowledged.json").read_text(encoding="utf-8"))
            self.assertEqual(ack["global_step"], 7)


if __name__ == "__main__":
    unittest.main()
