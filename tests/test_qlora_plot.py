import tempfile
import unittest
from pathlib import Path


class PlotTests(unittest.TestCase):
    def test_synthetic_fixture_plot_generation(self):
        try:
            import matplotlib  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            self.skipTest("Optional local plotting dependencies are unavailable")
        from training.plot import generate_plots
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Synthetic test data only; it is never written to an experiment output directory.
            (root / "training_events.jsonl").write_text(
                '{"event":"log","global_step":1,"loss":2.0,"learning_rate":0.1,"grad_norm":1.0,"gpu_allocated_bytes":10}\n'
                '{"event":"log","global_step":2,"eval_loss":1.8,"learning_rate":0.08,"gpu_reserved_bytes":20}\n'
                '{"event":"epoch_end","global_step":2,"epoch_duration_seconds":3.0}\n', encoding="utf-8")
            outputs = generate_plots(root)
            self.assertTrue(outputs)
            self.assertTrue(all(path.stat().st_size > 0 for path in outputs))
            self.assertTrue((root / "plot_manifest.json").is_file())


if __name__ == "__main__": unittest.main()
