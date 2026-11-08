import json
import tempfile
import unittest
from pathlib import Path

from recovery.phobert.restore import _sha256, execute


class PhoBERTRestoreTests(unittest.TestCase):
    def _manifest(self, root: Path, content: bytes = b"checkpoint") -> Path:
        bundle = root / "bundle"
        bundle.mkdir()
        (bundle / "weights.bin").write_bytes(content)
        manifest = root / "manifest.json"
        manifest.write_text(
            json.dumps({
                "schema_version": 1,
                "bundle_dir": str(bundle),
                "runtime_dir": str(root / "runtime"),
                "files": {"weights.bin": _sha256(bundle / "weights.bin")},
            }),
            encoding="utf-8",
        )
        (root / "pyproject.toml").touch()
        return manifest

    def test_restore_copies_a_valid_bundle(self) -> None:
        with tempfile.TemporaryDirectory(dir="tmp") as directory:
            root = Path(directory)
            result = execute(self._manifest(root))
            self.assertEqual(result["status"], "complete")
            self.assertEqual((root / "runtime" / "weights.bin").read_bytes(), b"checkpoint")

    def test_restore_rejects_checksum_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir="tmp") as directory:
            root = Path(directory)
            manifest = self._manifest(root)
            (root / "bundle" / "weights.bin").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                execute(manifest)

    def test_restore_refuses_to_overwrite_runtime(self) -> None:
        with tempfile.TemporaryDirectory(dir="tmp") as directory:
            root = Path(directory)
            manifest = self._manifest(root)
            (root / "runtime").mkdir()
            with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                execute(manifest)


if __name__ == "__main__":
    unittest.main()
