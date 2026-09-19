import unittest
import json
import tempfile
from pathlib import Path

from src.chunking.markdown import TTHCChunkingError, TTHCStructureAwareChunker


class TTHCStructureAwareChunkerTests(unittest.TestCase):
    def test_pdf_broken_word_row_is_rejoined_before_chunking(self):
        text = '# Thủ tục mẫu\nMã: 1.000005\n## Hồ sơ hải quan\n|Tên giấy tờ|Mẫu đơn|Số lượng|\n|---|---|---|\n|h) Gửi các chứng t||1 bản chính|\n\n|ừ quy định tại Điểm b, Điểm c.||\n|---|---|\n|g) Văn bản xác nhận của cơ quan|1 bản sao|'
        chunks = self.chunker.process_document(text)
        required = [c for c in chunks if c['section_type'] == 'required_documents']
        self.assertTrue(required)
        self.assertTrue(any('|h) Gửi các chứng từ quy định tại Điểm b, Điểm c.||1 bản chính|' in c['text_content'] for c in required))
        self.assertTrue(all('|ừ ' not in c['parent_section'] for c in required))
        self.assertTrue(all(c['text_content'].split('\n\n', 1)[1].startswith('|Tên giấy tờ|') for c in required))

    def test_serialized_json_has_no_break_tags_or_old_labels(self):
        from src.ingestion.parse import parse_pdf_to_hybrid_data
        markdown = '# CHI TIẾT THỦ TỤC HÀNH CHÍNH\nTên thủ tục: Hải quan bằng&amp;lt;br /&amp;gt;đường ống\nMã: 1.000005\n## CƠ QUAN THỰC HIỆN\nCơ quan hải quan địa phương\n## KẾT QUẢ XỬ LÝ\nThông quan hàng hóa theo quy định'
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'sample.pdf'
            source.write_bytes(b'%PDF-1.4\n')
            output, _ = parse_pdf_to_hybrid_data(source, markdown_converter=lambda _: markdown, output_dir=directory)
            chunks = json.loads(output.read_text(encoding='utf-8'))
        self.assertTrue(chunks)
        for chunk in chunks:
            self.assertEqual(chunk['procedure_name'], 'Hải quan bằng đường ống')
            self.assertEqual(chunk['section_type'], 'metadata_identity')
            self.assertNotIn('br', chunk['context_prefix'])

    def test_incomplete_long_table_row_is_rejected_not_word_split(self):
        row = '| ' + 'gửi các chứng từ ' * 150
        markdown = '# Thủ tục mẫu\nMã: 1.000005\n## Giấy tờ\n| Tên giấy tờ |\n|---|\n' + row
        with self.assertRaisesRegex(TTHCChunkingError, 'table row'):
            self.chunker.process_document(markdown)

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

    def test_generic_detail_heading_is_metadata_identity(self):
        self.assertEqual(self.chunker.classify_section("CHI TIẾT THỦ TỤC HÀNH CHÍNH"), "metadata_identity")

    def test_large_table_repeats_bold_header_for_every_sub_chunk(self):
        rows = "\n".join(f"| Chứng từ số {index} | " + "Mô tả dài " * 12 + "|" for index in range(18))
        header = "| **Tên giấy tờ** | **Mô tả** |"
        markdown = f"# Khai báo hải quan\n\nMã TTHC: 1.000005\n\n## Hồ sơ hải quan\n\n{header}\n|---|---|\n{rows}"
        chunks = [chunk for chunk in self.chunker.process_document(markdown) if chunk["section_type"] == "required_documents"]
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk["text_content"].split("\n\n", 1)[1].startswith(header) for chunk in chunks))

    def test_table_header_is_repeated_for_plain_text_continuation(self):
        header = "| **Tên giấy tờ** | **Mẫu đơn, tờ khai** | **Số lượng** |"
        rows = "\n".join(f"| Giấy tờ {index} | Mẫu {index} | 01 |" for index in range(35))
        continuation = "\n\n" + "Nội dung tiếp nối của ô trong bảng. " * 55
        markdown = f"# Khai báo hải quan\n\nMã TTHC: 1.000005\n\n## Hồ sơ hải quan\n\n{header}\n|---|---|---|\n{rows}{continuation}"
        chunks = [chunk for chunk in self.chunker.process_document(markdown) if chunk["section_type"] == "required_documents"]
        self.assertGreater(len(chunks), 2)
        self.assertTrue(all(chunk["text_content"].split("\n\n", 1)[1].startswith(header) for chunk in chunks))
        self.assertTrue(all(len(chunk["text_content"]) <= 1500 for chunk in chunks))

    def test_heading_only_or_too_short_chunk_is_filtered(self):
        markdown = "# Thủ tục mẫu\n\nMã TTHC: 1.000005\n\n## Căn cứ pháp lý\n\nNgắn"
        chunks = self.chunker.process_document(markdown)
        self.assertFalse(any(chunk["section_type"] == "legal_basis" for chunk in chunks))

    def test_html_is_removed_before_context_injection(self):
        for br in ("<br />", "<BR>", "<br/>", "&lt;br /&gt;"):
            with self.subTest(br=br):
                text = f"# CHI TIẾT THỦ TỤC HÀNH CHÍNH\nTên thủ tục: Hải quan bằng{br}đường ống\nMã: 1.000005\n## CƠ QUAN{br}THỰC HIỆN\nCơ quan hải quan địa phương.\n## KẾT QUẢ XỬ LÝ\nThông quan hàng hóa theo hồ sơ."
                chunks = self.chunker.process_document(text)
                self.assertTrue(all(c["procedure_name"] == "Hải quan bằng đường ống" for c in chunks))
                self.assertTrue(all(c["section_type"] == "metadata_identity" for c in chunks))
                self.assertTrue(all("<" not in c["text_content"] for c in chunks))

    def test_multiple_tables_use_their_own_headers(self):
        first = "| Tên giấy tờ | Số lượng |\n|---|---|\n| Giấy chứng nhận đầu tiên | 01 |"
        second = "| Mẫu đơn | Ghi chú |\n|---|---|\n" + "\n".join(f"| Mẫu số {i} | Nội dung chi tiết cần kiểm tra |" for i in range(70))
        text = f"# Thủ tục mẫu\nMã: 1.000005\n## Giấy tờ\n{first}\n\n{second}"
        chunks = self.chunker.process_document(text)
        selected = [c for c in chunks if "| Mẫu số" in c["text_content"]]
        self.assertGreater(len(selected), 1)
        for chunk in selected:
            self.assertTrue(chunk["text_content"].split("\n\n", 1)[1].startswith("| Mẫu đơn | Ghi chú |"))
            self.assertNotIn("| Tên giấy tờ |", chunk["text_content"])
            self.assertLessEqual(len(chunk["text_content"]), 1500)
        for i in range(70):
            self.assertTrue(any(f"| Mẫu số {i} |" in c["text_content"] for c in selected))

    def test_header_only_table_is_filtered(self):
        chunks = self.chunker.process_document("# Thủ tục mẫu\nMã: 1.000005\n## Giấy tờ\n| Tên giấy tờ | Số lượng |\n|---|---|")
        self.assertFalse(any(c["section_type"] == "required_documents" for c in chunks))


if __name__ == "__main__":
    unittest.main()
