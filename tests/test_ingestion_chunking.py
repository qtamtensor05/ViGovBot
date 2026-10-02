"""Regression tests for PDF boundaries, review routing, and chunk preservation."""

import json
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vigovbot.chunking.markdown import TTHCStructureAwareChunker, TTHCChunkingError, sanitize_text
from vigovbot.configuration import IngestionSettings, load_configuration
from vigovbot.ingestion.recovery import extract_pdf
from vigovbot.pipelines.indexing import (
    ConfigurationError,
    clean_markdown,
    main as ingestion_main,
    parse_pdf_to_hybrid_data,
    validate_pdf,
    write_json_atomic,
)

SAMPLE = """# Cấp bản sao trích lục hộ tịch

**Mã thủ tục:** 1.000005

## Thành phần hồ sơ

| Giấy tờ | Số lượng |
|---|---:|
| Tờ khai theo mẫu | 01 |

## Trình tự thực hiện

Người yêu cầu nộp hồ sơ và nhận kết quả tại cơ quan đăng ký hộ tịch.
"""


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pdf = self.root / "1.000005.pdf"
        self.pdf.write_bytes(b"%PDF-1.7\nsynthetic input for injected converter")

    def test_pdf_signature_size_and_extension(self):
        validate_pdf(self.pdf, 1000)
        with self.assertRaises(ConfigurationError):
            validate_pdf(self.pdf, 5)
        self.pdf.write_bytes(b"not a pdf")
        with self.assertRaises(ConfigurationError):
            validate_pdf(self.pdf, 1000)
        with self.assertRaises(ConfigurationError):
            validate_pdf(self.root / "absent.txt", 1000)

    def test_markdown_to_chunks_and_success_report(self):
        output, count = parse_pdf_to_hybrid_data(
            self.pdf, output_dir=self.root / "out", markdown_converter=lambda _: SAMPLE
        )
        records = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(count, len(records))
        self.assertGreater(count, 0)
        self.assertEqual(len({row["chunk_id"] for row in records}), count)
        self.assertTrue(all(row["source_code"] == "1.000005" for row in records))
        self.assertTrue(all(len(row["text_content"]) <= 1500 for row in records))
        report = json.loads((self.root / "out/reports/1.000005.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "success")

    def test_extraction_failure_leaves_report_not_chunks(self):
        def fail(_):
            raise RuntimeError("OCR failed")

        with self.assertRaisesRegex(RuntimeError, "OCR failed"):
            parse_pdf_to_hybrid_data(self.pdf, output_dir=self.root / "out", markdown_converter=fail)
        self.assertFalse((self.root / "out/1.000005.json").exists())
        report = json.loads((self.root / "out/reports/1.000005.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "failed")

    def test_partial_pages_are_routed_to_review(self):
        with patch(
            "vigovbot.pipelines.indexing.extract_pdf",
            return_value=(SAMPLE, {"pages": [], "missing_pages": [2], "warnings": ["extraction-warning"]}),
        ):
            output, _ = parse_pdf_to_hybrid_data(self.pdf, output_dir=self.root / "out")
        self.assertEqual(output.parent.name, "review")
        report = json.loads((self.root / "out/reports/1.000005.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "partial_success")
        self.assertIn("extraction-warning", report["warnings"])

    def test_metadata_recovery_requires_review(self):
        output, _ = parse_pdf_to_hybrid_data(
            self.pdf,
            output_dir=self.root / "out",
            markdown_converter=lambda _: "# Thủ tục thử nghiệm\n\nNội dung không có mã thủ tục, cần xác minh nguồn.",
        )
        self.assertEqual(output.parent.name, "review")

    def test_failed_atomic_write_preserves_previous_output(self):
        path = self.root / "result.json"
        write_json_atomic(path, {"valid": True})
        with self.assertRaises(TypeError):
            write_json_atomic(path, {"invalid": object()})
        self.assertEqual(json.loads(path.read_text()), {"valid": True})
        self.assertFalse(list(self.root.glob("*.tmp")))

    def test_chunker_preserves_content_and_table_context(self):
        chunker = TTHCStructureAwareChunker()
        first = chunker.process_document(SAMPLE, "1.000005.pdf")
        second = chunker.process_document(SAMPLE, "1.000005.pdf")
        self.assertEqual(first, second)
        combined = "\n".join(r["text_content"] for r in first)
        self.assertIn("Tờ khai theo mẫu", combined)
        self.assertIn("Người yêu cầu", combined)
        self.assertTrue(all(r["text_content"].startswith(r["context_prefix"]) for r in first))
        with self.assertRaises(TTHCChunkingError):
            chunker.process_document("")

    def test_html_cleanup_preserves_markdown_and_code(self):
        text = "<b>Hồ sơ</b><br>&amp;amp; giấy tờ\n| Cột |\n|---|\n| Nội dung |"
        self.assertEqual(sanitize_text(text), "Hồ sơ & giấy tờ\n| Cột |\n|---|\n| Nội dung |")
        self.assertIn("`code`", clean_markdown("Giữ `code` và bỏ `` token"))

    def test_packaged_defaults_work_outside_checkout(self):
        with patch("pathlib.Path.cwd", return_value=self.root), patch("pathlib.Path.is_file", return_value=False):
            config, _, _ = load_configuration()
        # Windows TEMP may use an 8.3 alias (e.g. RUNNER~1); config paths are resolved.
        self.assertEqual(config.output, (self.root / "outputs/metadata").resolve())

    def test_unread_scan_is_missing_not_blank(self):
        class Page:
            def get_text(self, **kwargs):
                return ""

            def get_images(self):
                return [object()]

            def get_drawings(self):
                return []

            def annots(self):
                return []

        class Document:
            needs_pass = False

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def __iter__(self):
                return iter([Page()])

        with patch.dict(
            "sys.modules",
            {"pymupdf": types.SimpleNamespace(open=lambda _: Document()), "pymupdf4llm": types.SimpleNamespace()},
        ):
            text, report = extract_pdf(str(self.pdf), IngestionSettings(ocr={"enabled": False}))
        self.assertEqual(text, "")
        self.assertEqual(report["missing_pages"], [1])
        self.assertEqual(report["pages"][0]["method"], "failed")

    def test_batch_workers_process_files_concurrently(self):
        input_dir = self.root / "pdfs"
        output_dir = self.root / "out"
        input_dir.mkdir()
        for index in range(3):
            (input_dir / f"{index}.pdf").write_bytes(b"%PDF-1.7\nsynthetic")

        root = SimpleNamespace(input=input_dir, output=output_dir, overwrite=False)
        ingestion = IngestionSettings()
        state = {"active": 0, "maximum": 0}
        lock = threading.Lock()

        def fake_parse(file, *, output_dir, config_path):
            with lock:
                state["active"] += 1
                state["maximum"] = max(state["maximum"], state["active"])
            time.sleep(0.05)
            with lock:
                state["active"] -= 1
            return output_dir / f"{file.stem}.json", 1

        with (
            patch("vigovbot.pipelines.indexing.load_configuration", return_value=(root, ingestion, object())),
            patch("vigovbot.pipelines.indexing.parse_pdf_to_hybrid_data", side_effect=fake_parse),
        ):
            result = ingestion_main(["--workers", "3"])

        self.assertEqual(result, 0)
        self.assertGreater(state["maximum"], 1)

    def test_workers_must_be_positive(self):
        self.assertEqual(ingestion_main(["--workers", "0"]), 1)


if __name__ == "__main__":
    unittest.main()
