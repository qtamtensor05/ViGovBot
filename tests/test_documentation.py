from tests.dependencies import skip_missing_dependency  # noqa: F401

import re
import unittest
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {".git", "Data", "env", "outputs"}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


class DocumentationTests(unittest.TestCase):
    def test_local_markdown_links_resolve(self):
        broken: list[str] = []
        for document in ROOT.rglob("*.md"):
            if any(part in IGNORED_PARTS for part in document.relative_to(ROOT).parts):
                continue
            text = document.read_text(encoding="utf-8-sig")
            for raw_target in MARKDOWN_LINK.findall(text):
                target = raw_target.strip()
                if target.startswith("<") and target.endswith(">"):
                    target = target[1:-1]
                elif " " in target:
                    target = target.split(" ", 1)[0]
                target = unquote(target.split("#", 1)[0])
                if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                    continue
                resolved = (document.parent / target).resolve()
                try:
                    target_parts = resolved.relative_to(ROOT).parts
                except ValueError:
                    target_parts = ()
                if target_parts and target_parts[0] in {"Data", "outputs"}:
                    continue
                if not resolved.exists():
                    broken.append(f"{document.relative_to(ROOT)} -> {target}")
        self.assertEqual(broken, [], "Broken local Markdown links:\n" + "\n".join(broken))


if __name__ == "__main__":
    unittest.main()
