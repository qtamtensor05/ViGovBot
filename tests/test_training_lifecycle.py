from tests.dependencies import skip_missing_dependency

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    from vigovbot.training import lifecycle
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


class TrainingLifecycleTests(unittest.TestCase):
    def _validation(self, root: Path) -> dict:
        config = root / "configs" / "gpu.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("fixture", encoding="utf-8")
        return {
            "config": str(config),
            "output_root": str(root / "outputs" / "qlora"),
            "total_steps": 4,
            "resume_step": 0,
            "run_dir": None,
        }

    def test_start_dry_run_creates_no_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            validation = self._validation(root)
            with patch.object(lifecycle, "validate_launch", return_value=validation):
                result = lifecycle.start(validation["config"], run_id="smoke-safe", dry_run=True)
            self.assertEqual(result["mode"], "DRY_RUN")
            self.assertFalse((root / "outputs").exists())

    def test_start_persists_identity_and_rejects_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            validation = self._validation(root)
            fake_process = Mock(pid=321)
            fake_psutil = Mock()
            fake_psutil.create_time.return_value = 123.0
            with patch.object(lifecycle, "validate_launch", return_value=validation), \
                    patch.object(lifecycle.subprocess, "Popen", return_value=fake_process), \
                    patch.object(lifecycle.psutil, "Process", return_value=fake_psutil), \
                    patch.object(lifecycle, "_process_matches", return_value=True), \
                    patch.object(lifecycle.time, "sleep"):
                state = lifecycle.start(validation["config"], run_id="smoke-safe")
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    lifecycle.start(validation["config"], run_id="other")
            persisted = json.loads(Path(state["stdout_log"]).parent.joinpath("process.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["worker_pid"], 321)
            self.assertEqual(persisted["worker_create_time"], 123.0)

    def test_status_requires_matching_pid_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "outputs" / "qlora"
            state_path = output / "control" / "runs" / "run-a" / "start-a" / "process.json"
            state_path.parent.mkdir(parents=True)
            state = {"run_id": "run-a", "run_dir": str(output / "run-a"), "worker_pid": 10,
                     "worker_create_time": 1.0, "training_pid": 11, "training_create_time": 2.0}
            state_path.write_text(json.dumps(state), encoding="utf-8")
            active = output / "control" / "active_run.json"
            active.write_text(json.dumps({"state_path": str(state_path)}), encoding="utf-8")
            with patch.object(lifecycle, "_process_matches", side_effect=[False, False]):
                result = lifecycle.inspect(output)
            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["worker_identity_verified"])
            self.assertFalse(result["training_identity_verified"])

    def test_stop_never_signals_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "outputs" / "qlora"
            state_path = output / "control" / "runs" / "run-a" / "start-a" / "process.json"
            state_path.parent.mkdir(parents=True)
            state = {"run_id": "run-a", "run_dir": str(output / "run-a"), "training_pid": 99,
                     "training_create_time": 2.0}
            state_path.write_text(json.dumps(state), encoding="utf-8")
            (output / "control" / "active_run.json").write_text(
                json.dumps({"state_path": str(state_path)}), encoding="utf-8")
            with patch.object(lifecycle, "_process_matches", return_value=False), \
                    patch.object(lifecycle.psutil, "Process") as process:
                result = lifecycle.request_stop(output, timeout=1, force=True)
            self.assertEqual(result["status"], "not_running")
            process.assert_not_called()

    def test_dashboard_is_detached_and_duplicate_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "outputs" / "qlora"
            output.mkdir(parents=True)
            fake_process = Mock(pid=654)
            process_info = Mock()
            process_info.create_time.return_value = 456.0
            with patch.object(lifecycle.subprocess, "Popen", return_value=fake_process), \
                    patch.object(lifecycle.psutil, "Process", return_value=process_info):
                state = lifecycle.start_dashboard(output, port=6123)
            self.assertEqual(state["pid"], 654)
            self.assertEqual(state["url"], "http://127.0.0.1:6123")
            with patch.object(lifecycle, "_process_matches", return_value=True):
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    lifecycle.start_dashboard(output, port=6123)


if __name__ == "__main__":
    unittest.main()
