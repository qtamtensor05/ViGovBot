"""Setup boundaries: remote services, model arguments and installer isolation."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vigovbot.utils.colab_runtime import ensure_ollama


class ColabRuntimeTests(unittest.TestCase):
    def test_remote_service_never_installs_or_starts_local_process(self):
        with (
            patch("vigovbot.utils.colab_runtime.check_model", return_value={"digest": "abc"}) as check,
            patch("vigovbot.utils.colab_runtime.run_local") as run,
            patch("vigovbot.utils.colab_runtime.subprocess.Popen") as start,
        ):
            self.assertEqual(ensure_ollama(base_url="https://ollama.example"), {"digest": "abc"})
            check.assert_called_once_with("https://ollama.example", "qwen2.5:7b")
            run.assert_not_called()
            start.assert_not_called()

    def test_invalid_model_and_url_rejected_before_network(self):
        with patch("vigovbot.utils.colab_runtime.requests.get") as get:
            for model in ("--help", "x;touch file", "x\ncommand", ""):
                with self.subTest(model=model), self.assertRaises(ValueError):
                    ensure_ollama(model=model)
            for url in ("file:///tmp/ollama", "http://user:secret@localhost:11434", "not-a-url"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    ensure_ollama(base_url=url)
            get.assert_not_called()

    def test_installer_uses_private_temporary_file_and_cleans_up(self):
        scripts = []

        def run(command, **kwargs):
            if Path(command[0]).name == "sh":
                script = Path(command[1])
                self.assertEqual(script.read_bytes(), b"trusted-test-installer")
                self.assertTrue(script.parent.name.startswith("vigovbot-ollama-install-"))
                scripts.append(script)

        response = Mock(content=b"trusted-test-installer", ok=True)
        with (
            patch("vigovbot.utils.colab_runtime.shutil.which", return_value=None),
            patch("vigovbot.utils.colab_runtime.os.path.isdir", return_value=True),
            patch("vigovbot.utils.colab_runtime.executable", side_effect=lambda name: str(Path(name).resolve())),
            patch("vigovbot.utils.colab_runtime.requests.get", return_value=response),
            patch("vigovbot.utils.colab_runtime.run_local", side_effect=run),
            patch("vigovbot.utils.colab_runtime.check_model", return_value={}),
        ):
            ensure_ollama()
        self.assertEqual(len(scripts), 1)
        self.assertFalse(scripts[0].parent.exists())


if __name__ == "__main__":
    unittest.main()
