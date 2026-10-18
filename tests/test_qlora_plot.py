from tests.dependencies import skip_missing_dependency

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
        from vigovbot.training.plot import generate_plots
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
            self.assertTrue((root / "plots" / "plot_manifest.json").is_file())

    def test_report_reads_canonical_layout_and_writes_reports_section(self):
        try:
            from vigovbot.training.report import build_report
        except ModuleNotFoundError as exc:
            skip_missing_dependency(exc)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "metrics").mkdir()
            (root / "metrics" / "training_metrics.json").write_text(
                '{"status":"completed","best_validation_loss":0.25}', encoding="utf-8")
            output = build_report(root)
            self.assertEqual(output, root / "reports" / "summary_report.md")
            self.assertTrue((root / "reports" / "experiment_report.json").is_file())
            self.assertIn("0.25", output.read_text(encoding="utf-8"))


if __name__ == "__main__": unittest.main()
