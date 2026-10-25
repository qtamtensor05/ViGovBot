from tests.dependencies import skip_missing_dependency

import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from vigovbot.chunking.tables import flatten_tables, first_table_header, repeat_table_header, repair_table_continuations
    from vigovbot.training.config import load_config
    from vigovbot.training.train import _prepare_training_data
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


class RefactorBoundaryTests(unittest.TestCase):
    def test_tables_without_chunker_or_configuration(self):
        table = "| Tên | Phí |\n| --- | --- |\n| Hồ sơ | 0 đồng |"
        self.assertIn("Phí: 0 đồng", flatten_tables(table))
        header = first_table_header(table)
        self.assertEqual(repeat_table_header([table, "| Khác | 1 đồng |"], header)[1], header + "\n| Khác | 1 đồng |")
        self.assertEqual(repair_table_continuations(table), table)

    def test_resume_rejects_new_run_id_before_creating_run(self):
        with patch("vigovbot.training.train.dataset_paths", return_value={"train": Path("train"), "validation": Path("validation"), "test": Path("test")}), \
             patch("vigovbot.training.train.read_jsonl", return_value=[]), \
             patch("vigovbot.training.train.sha256_file", return_value="digest"), \
             patch("vigovbot.training.train.create_run_dir") as create:
            with self.assertRaisesRegex(ValueError, "cannot be combined"):
                _prepare_training_data(load_config("configs/training/base.yaml"), "checkpoint", "new-run")
            create.assert_not_called()
