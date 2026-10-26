from tests.dependencies import skip_missing_dependency  # noqa: F401
import unittest

from vigovbot.chunking.headings import extract_metadata, classify_section, TTHCChunkingError
from vigovbot.chunking.splitter import BlockSplitter


class ChunkingPrimitiveTests(unittest.TestCase):
    def test_metadata_and_heading_are_independent_of_pydantic(self):
        metadata = extract_metadata("# Cấp giấy phép\nMã: 1.000001")
        self.assertEqual(metadata, {"source_code": "1.000001", "procedure_name": "Cấp giấy phép"})
        self.assertEqual(classify_section("**Lệ phí**", {"submission_deadline_fee": ["le phi"]}), "submission_deadline_fee")
        with self.assertRaises(TTHCChunkingError):
            extract_metadata("# Không có mã")

    def test_character_budget_keeps_words_and_whole_table_rows(self):
        splitter = BlockSplitter(20, 5)
        text = "một hai ba bốn năm sáu bảy tám chín mười"
        pieces = splitter._split_plain_block(text, 20)
        self.assertEqual(" ".join(pieces), text)
        self.assertTrue(all(len(piece) <= 20 for piece in pieces))
        rows = ["| a | b |", "|---|---|", "| c | d |", "| e | f |"]
        tables = splitter._split_table(rows, 30)
        self.assertEqual(len(tables), 2)
        self.assertTrue(all(table.startswith("\n".join(rows[:2])) for table in tables))
        self.assertEqual(splitter._safe_overlap("\n".join(rows)), "")

    def test_table_without_trailing_pipe_repeats_column_headers(self):
        rows = ['| Name | Value', '|---|---', '| A | 10', '| B | 20']
        pieces = BlockSplitter(32, 0)._split_table(rows, 32)
        self.assertEqual(len(pieces), 2)
        self.assertTrue(all(piece.startswith('\n'.join(rows[:2])) for piece in pieces))
        self.assertIn(rows[2], pieces[0])
        self.assertIn(rows[3], pieces[1])
