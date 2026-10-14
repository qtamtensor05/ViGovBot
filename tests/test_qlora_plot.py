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
            (root / "training_log.csv").write_text("step,loss,eval_loss,learning_rate,grad_norm\n1,2.0,,0.1,1.0\n2,,1.8,0.08,\n", encoding="utf-8")
            outputs = generate_plots(root)
            self.assertTrue(outputs)
            self.assertTrue(all(path.stat().st_size > 0 for path in outputs))


if __name__ == "__main__": unittest.main()
