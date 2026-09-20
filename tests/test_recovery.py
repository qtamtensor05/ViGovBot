import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.chunking.markdown import TTHCStructureAwareChunker
from src.ingestion.parse import parse_pdf_to_hybrid_data
from src.ingestion.recovery import extract_pdf


class RecoveryTests(unittest.TestCase):
    def test_interrupt_writes_report_without_output(self):
        with tempfile.TemporaryDirectory() as root:
            pdf = Path(root) / '1.000005.pdf'
            pdf.write_bytes(b'%PDF-1.4')
            with patch('src.ingestion.parse.extract_pdf', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    parse_pdf_to_hybrid_data(pdf, output_dir=root)
            report = json.loads((Path(root) / 'reports' / '1.000005.json').read_text(encoding='utf-8'))
            self.assertEqual(report['status'], 'interrupted')
            self.assertFalse((Path(root) / '1.000005.json').exists())

    def test_long_prefix_and_header_preserve_parent(self):
        text = '# ' + 'Thủ tục rất dài ' * 150 + '\nMã: 1.000005\n## Giấy tờ\n'
        table = '| ' + 'Nhãn rất dài ' * 150 + '|Số lượng|\n|---|---|\n|Nội dung chứng từ cần lưu trữ|01|'
        chunks = TTHCStructureAwareChunker().process_document(text + table)
        self.assertTrue(all(len(c['text_content']) <= 1500 for c in chunks))
        self.assertTrue(any(table in c['parent_section'] for c in chunks))

    def test_missing_code_is_quarantined(self):
        with tempfile.TemporaryDirectory() as root:
            pdf = Path(root) / '1.0133611.pdf'
            pdf.write_bytes(b'%PDF-1.4')
            output, count = parse_pdf_to_hybrid_data(pdf, output_dir=root,
                markdown_converter=lambda _: '# Thủ tục không có mã\nNội dung hồ sơ đầy đủ cần được lưu trữ.')
            report = json.loads((Path(root) / 'reports' / '1.0133611.json').read_text(encoding='utf-8'))
            self.assertEqual(output.parent.name, 'review')
            self.assertEqual(report['status'], 'needs_review')
            self.assertGreater(count, 0)
            self.assertTrue(json.loads(output.read_text(encoding='utf-8'))[0]['source_code'].startswith('unverified_'))

    def test_partial_extraction_is_saved_with_missing_pages(self):
        with tempfile.TemporaryDirectory() as root:
            pdf = Path(root) / '1.000005.pdf'
            pdf.write_bytes(b'%PDF-1.4')
            extraction = ('# Thủ tục mẫu\nMã: 1.000005\nNội dung đã đọc được.',
                          {'pages': [], 'warnings': [], 'missing_pages': [2]})
            with patch('src.ingestion.parse.extract_pdf', return_value=extraction):
                output, _ = parse_pdf_to_hybrid_data(pdf, output_dir=root)
            self.assertEqual(output.parent.name, 'review')
            report = json.loads((Path(root) / 'reports' / '1.000005.json').read_text(encoding='utf-8'))
            self.assertEqual(report['status'], 'partial_success')
            self.assertEqual(report['missing_pages'], [2])

    def test_ocr_success_and_failure_are_reported_per_page(self):
        import pymupdf
        pages = [MagicMock(), MagicMock()]
        for page in pages:
            page.get_text.return_value = ''
            page.get_images.return_value = [(1,)]
        pages[0].get_text.side_effect = ['', 'Văn bản OCR tiếng Việt']
        pages[1].get_textpage_ocr.side_effect = RuntimeError('Missing vie.traineddata')
        doc = MagicMock()
        doc.needs_pass = False
        doc.__iter__.return_value = iter(pages)
        with patch.object(pymupdf, 'open') as opened:
            opened.return_value.__enter__.return_value = doc
            text, report = extract_pdf('scan.pdf')
        self.assertIn('Văn bản OCR', text)
        self.assertEqual(report['missing_pages'], [2])
        self.assertEqual(report['pages'][0]['method'], 'ocr')


if __name__ == '__main__':
    unittest.main()
