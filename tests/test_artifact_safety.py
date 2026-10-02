"""Integrity, compatibility, concurrency, and independent inference regressions."""

import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import numpy as np

from vigovbot.artifacts import (
    CORPUS_MANIFEST,
    embedding_identity,
    make_manifest,
    output_lock,
    publish,
)
from vigovbot.ingestion.unified import corpus_identity, verify_corpus
from vigovbot.rag.config import RAGConfig
from vigovbot.rag.pipeline import execute, inference_session
from vigovbot.vectordb.vector_store import prepare_corpus


class ArtifactSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def corpus(self):
        import faiss

        directory = self.root / "unified"
        directory.mkdir()
        index_path = directory / "tthc_unified.index"
        metadata = directory / "tthc_unified_metadata.json"
        matrix = np.zeros((1, 1024), dtype=np.float32)
        matrix[0, 0] = 1
        index = faiss.IndexFlatIP(1024)
        index.add(matrix)
        with index_path.open("wb") as handle:
            faiss.write_index(index, faiss.PyCallbackIOWriter(handle.write))
        record = dict(
            chunk_id="01",
            source_file="1.pdf",
            source_code="1.123456",
            procedure_name="Thủ tục",
            section_type="other",
            context_prefix="",
            text_content="Phí 0 đồng",
            parent_section="",
        )
        metadata.write_text(json.dumps([record]), encoding="utf-8")
        manifest = make_manifest("corpus", embedding_identity("a" * 40), 1, [index_path, metadata])
        path = directory / CORPUS_MANIFEST
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return directory

    def test_verified_round_trip_directory_and_nested_zip(self):
        source = self.corpus()
        _, manifest = verify_corpus(source)
        self.assertEqual(manifest["embedding"]["revision"], "a" * 40)
        archive = self.root / "corpus.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            for name in (*manifest["files"], CORPUS_MANIFEST):
                zf.write(source / name, "nested/" + name)
        self.assertEqual(corpus_identity(source), corpus_identity(archive))
        first = prepare_corpus(source, self.root / "cache")
        second = prepare_corpus(archive, self.root / "cache")
        self.assertEqual(first, second)

    def test_changed_corpus_rejected_before_faiss_deserialization(self):
        source = self.corpus()
        with (source / "tthc_unified.index").open("ab") as handle:
            handle.write(b"modified")
        with patch("faiss.read_index") as load, self.assertRaisesRegex(ValueError, "checksum"):
            prepare_corpus(source, self.root / "cache")
        load.assert_not_called()

    def test_content_identity_detects_same_size_same_mtime_change(self):
        source = self.corpus()
        before = corpus_identity(source)
        path = source / "tthc_unified_metadata.json"
        stat = path.stat()
        content = path.read_bytes().replace(b'"01"', b'"02"')
        self.assertEqual(len(content), stat.st_size)
        path.write_bytes(content)
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertNotEqual(before, corpus_identity(source))

    def test_corrupt_cache_rebuilt(self):
        source = self.corpus()
        index, database, info = prepare_corpus(source, self.root / "cache")
        index.write_bytes(b"corrupt")
        database.write_bytes(b"corrupt")
        rebuilt = prepare_corpus(source, self.root / "cache")
        self.assertEqual(rebuilt[2]["cache_sha256"], info["cache_sha256"])

    def test_manifest_cannot_supply_external_paths(self):
        source = self.corpus()
        path = source / CORPUS_MANIFEST
        manifest = json.loads(path.read_text())
        manifest["files"]["../../outside"] = "a" * 64
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "checksums"):
            verify_corpus(source)

    def test_modified_cache_provenance_cannot_change_encoder(self):
        source = self.corpus()
        index, _, _ = prepare_corpus(source, self.root / "cache")
        marker = index.parent / "ready.json"
        info = json.loads(marker.read_text())
        info["embedding"]["revision"] = "b" * 40
        marker.write_text(json.dumps(info))
        self.assertEqual(prepare_corpus(source, self.root / "cache")[2]["embedding"]["revision"], "a" * 40)

    def test_session_loads_revision_from_manifest_and_closes_on_failure(self):
        source = self.corpus()
        paths = prepare_corpus(source, self.root / "cache")
        config = RAGConfig.model_validate({"data": {"unified_source": source}})
        tokenizer_module = types.SimpleNamespace(
            AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda *a, **kw: object())
        )
        torch_module = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
        with (
            patch.dict("sys.modules", {"transformers": tokenizer_module, "torch": torch_module}),
            patch("vigovbot.rag.pipeline.load_encoder", return_value=object()) as encoder,
            patch("vigovbot.rag.pipeline.Retriever") as retriever,
            patch("vigovbot.rag.pipeline.unload_model") as unload,
        ):
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                with inference_session(config, paths):
                    raise RuntimeError("interrupted")
            self.assertEqual(encoder.call_args.kwargs["revision"], "a" * 40)
            retriever.return_value.close.assert_called_once()
            unload.assert_called_once()

    def test_failed_publication_rolls_back_own_files(self):
        stage, output = self.root / "stage", self.root / "out"
        stage.mkdir()
        output.mkdir()
        (stage / "a").write_text("a")
        with self.assertRaises(FileNotFoundError):
            publish(stage, output, ["a", "missing"], "manifest.json", {})
        self.assertEqual(list(output.iterdir()), [])

    def test_concurrent_writer_rejected_and_lock_released(self):
        with output_lock(self.root):
            with self.assertRaisesRegex(RuntimeError, "Another process"):
                with output_lock(self.root):
                    self.fail("Concurrent writer entered")
        with output_lock(self.root):
            pass

    def test_prepare_and_ask_do_not_read_evaluation_dataset(self):
        source = self.corpus()
        config = RAGConfig.model_validate(
            {"data": {"unified_source": source, "cache_dir": self.root / "cache", "output_dir": self.root / "results"}}
        )

        @contextmanager
        def session(config, paths):
            yield object(), object()

        with patch("vigovbot.rag.pipeline.select_cases", side_effect=AssertionError("Dataset accessed")):
            self.assertEqual(execute(config, "prepare")["count"], 1)
            with (
                patch("vigovbot.rag.pipeline.check_model", return_value={}),
                patch("vigovbot.rag.pipeline.inference_session", side_effect=session),
                patch("vigovbot.rag.pipeline.answer_question", return_value={"prediction": "0 đồng"}) as answer,
            ):
                self.assertEqual(execute(config, "ask", question="Phí?"), {"prediction": "0 đồng"})
                self.assertEqual(answer.call_args.args[0], "Phí?")
        self.assertFalse(config.data.output_dir.exists())
        with self.assertRaisesRegex(ValueError, "Evaluation requires"):
            execute(config, "evaluate")

    def test_wrong_query_model_or_revision_rejected_before_model_load(self):
        source = self.corpus()
        for embedding in ({"model": "other"}, {"revision": "b" * 40}):
            config = RAGConfig.model_validate(
                {"data": {"unified_source": source, "cache_dir": self.root / "cache"}, "embedding": embedding}
            )
            with (
                patch("vigovbot.rag.pipeline.check_model") as model,
                self.assertRaisesRegex(ValueError, "does not match"),
            ):
                execute(config, "ask", question="Phí?")
            model.assert_not_called()

    def test_invalid_cli_command_and_question_rejected(self):
        config = RAGConfig.model_validate({"data": {"unified_source": "absent"}})
        with self.assertRaisesRegex(ValueError, "Unknown command"):
            execute(config, "typo")
        with self.assertRaisesRegex(ValueError, "nonempty"):
            execute(config, "ask", question="  ")

    def test_console_utf8_with_redirected_cp1252_stream(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from vigovbot.console import configure_console; configure_console(); print('Thủ tục tiếng Việt')",
            ],
            env={**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"},
            capture_output=True,
            check=True,
        )
        self.assertEqual(result.stdout.decode("utf-8").strip(), "Thủ tục tiếng Việt")


if __name__ == "__main__":
    unittest.main()
