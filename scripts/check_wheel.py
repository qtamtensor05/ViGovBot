"""Install the built wheel outside the checkout and check packaged defaults/CLI."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    wheels = sorted((root / "dist").glob("vigovbot-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Expected exactly one built vigovbot wheel in dist/")
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        target = work / "installed"
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), str(wheels[0])], check=True
        )
        env = {**os.environ, "PYTHONPATH": str(target)}
        code = (
            "from pathlib import Path; import vigovbot; "
            "assert Path(vigovbot.__file__).resolve().is_relative_to(Path('installed').resolve()); "
            "from vigovbot.configuration import load_configuration; "
            "config, ingestion, chunking = load_configuration(); "
            "assert config.output == (Path.cwd() / 'outputs/metadata').resolve(); "
            "assert chunking.max_chars == 1500; print('Wheel defaults OK')"
        )
        subprocess.run([sys.executable, "-c", code], cwd=work, env=env, check=True)
        for args in (["--help"], ["ingest", "--help"], ["embed", "--help"], ["merge", "--help"], ["rag", "--help"]):
            subprocess.run([sys.executable, "-m", "vigovbot", *args], cwd=work, env=env, check=True)


if __name__ == "__main__":
    main()
