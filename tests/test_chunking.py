import unittest

from src.chunking.markdown import TTHCChunkingError, TTHCStructureAwareChunker


class TTHCStructureAwareChunkerTests(unittest.TestCase):
    def setUp(self):
        self.chunker = TTHCStructureAwareChunker()

    def test_schema_context_and_classification(self):
        markdown = """# Cấp bản sao trích lục hộ tịch

Mã TTHC: 1.000005

## Thành phần hồ sơ

Tờ khai theo mẫu và giấy tờ tùy thân.
"""
        chunks = self.chunker.process_document(markdown, "1.000005.pdf")
        required = next(chunk for chunk in chunks if chunk["section_type"] == "required_documents")
        self.assertEqual(required["source_code"], "1.000005")
        self.assertTrue(required["text_content"].startswith(required["context_prefix"]))
        self.assertEqual(set(required), {"chunk_id", "source_file", "source_code", "procedure_name", "section_type", "context_prefix", "text_content", "parent_section"})

    def test_small_table_remains_intact(self):
        table = "| Giấy tờ | Số lượng |\n|---|---:|\n| Tờ khai | 01 |"
        markdown = f"# Đăng ký hộ tịch\n\nMã TTHC: 1.000005\n\n## Giấy tờ\n\n{table}"
        chunks = self.chunker.process_document(markdown)
        table_chunks = [chunk for chunk in chunks if "| Giấy tờ |" in chunk["text_content"]]
        self.assertEqual(len(table_chunks), 1)
        self.assertIn(table, table_chunks[0]["text_content"])

    def test_long_section_obeys_hard_limit_and_keeps_parent(self):
        paragraphs = "\n\n".join(f"Đoạn {index}: " + "nội dung hồ sơ " * 18 for index in range(12))
        markdown = f"# Đăng ký hộ tịch\n\nMã TTHC: 1.000005\n\n## Trình tự thực hiện\n\n{paragraphs}"
        chunks = self.chunker.process_document(markdown)
        steps = [chunk for chunk in chunks if chunk["section_type"] == "procedure_step"]
        self.assertGreater(len(steps), 1)
        self.assertTrue(all(len(chunk["text_content"]) <= 1500 for chunk in steps))
        self.assertEqual(len({chunk["parent_section"] for chunk in steps}), 1)

    def test_missing_required_metadata_is_reported(self):
        with self.assertRaises(TTHCChunkingError):
            self.chunker.process_document("## Thành phần hồ sơ\n\nTờ khai")

    def test_generic_page_title_is_ignored_and_name_after_label_is_used(self):
        markdown = """# CHI TIẾT THỦ TỤC HÀNH CHÍ

**Tên thủ tục**

Cấp giấy phép xử lý chất thải nguy hại

Mã TTHC: 1.000005
"""
        chunks = self.chunker.process_document(markdown)
        self.assertTrue(chunks)
        self.assertTrue(all(chunk["procedure_name"] == "Cấp giấy phép xử lý chất thải nguy hại" for chunk in chunks))

    def test_name_with_colon_inside_bold_markup(self):
        markdown = "# CHI TIẾT THỦ TỤC HÀNH CHÍ\n\n**Tên thủ tục:** Cấp phép nhập khẩu\n\nMã TTHC: 1.000005"
        chunks = self.chunker.process_document(markdown)
        self.assertTrue(all(chunk["procedure_name"] == "Cấp phép nhập khẩu" for chunk in chunks))

    def test_additional_required_document_keywords(self):
        self.assertEqual(self.chunker.classify_section("Chứng từ phải nộp"), "required_documents")
        self.assertEqual(self.chunker.classify_section("Hồ sơ hải quan"), "required_documents")

    def test_large_table_repeats_bold_header_for_every_sub_chunk(self):
        rows = "\n".join(f"| Chứng từ số {index} | " + "Mô tả dài " * 12 + "|" for index in range(18))
        header = "| **Tên giấy tờ** | **Mô tả** |"
        markdown = f"# Khai báo hải quan\n\nMã TTHC: 1.000005\n\n## Hồ sơ hải quan\n\n{header}\n|---|---|\n{rows}"
        chunks = [chunk for chunk in self.chunker.process_document(markdown) if chunk["section_type"] == "required_documents"]
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(header in chunk["text_content"] for chunk in chunks))

    def test_heading_only_or_too_short_chunk_is_filtered(self):
        markdown = "# Thủ tục mẫu\n\nMã TTHC: 1.000005\n\n## Căn cứ pháp lý\n\nNgắn"
        chunks = self.chunker.process_document(markdown)
        self.assertFalse(any(chunk["section_type"] == "legal_basis" for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
