"""Reinstall the lightweight test lock in a temporary isolated venv and run tests."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def main():
    root = Path(__file__).resolve().parents[1]
    if sys.platform != "win32" or sys.version_info[:2] != (3, 14):
        raise RuntimeError("This check targets locks/test-windows-py314.txt")
    with tempfile.TemporaryDirectory(prefix="vigovbot-clean-") as work:
        venv.EnvBuilder(with_pip=True).create(work)
        python = Path(work) / "Scripts/python.exe"
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", str(root / "locks/test-windows-py314.txt")],
            cwd=root,
            check=True,
        )
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", "-e", str(root)], check=True)
        subprocess.run([str(python), "-m", "pip", "check"], check=True)
        env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
        subprocess.run([str(python), "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=root, env=env, check=True)
        subprocess.run([str(python), "scripts/demo_offline.py"], cwd=root, env=env, check=True)


if __name__ == "__main__":
    main()
