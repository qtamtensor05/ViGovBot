"""Install the built wheel outside the checkout and check packaged defaults/CLI."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-dir", type=Path, default=root / "dist")
    args = parser.parse_args()
    wheels = sorted(args.wheel_dir.resolve().glob("vigovbot-*.whl"))
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
        for args in (["--help"], ["ingest", "--help"], ["embed", "--help"], ["rag", "--help"]):
            subprocess.run([sys.executable, "-m", "vigovbot", *args], cwd=work, env=env, check=True)
        # Resolve installed console entrypoints, not only the compatibility module.
        for entrypoint in ("vigov", "vigovbot"):
            for command in ([], ["train"], ["eva"], ["data"], ["doctor"]):
                invocation = (
                    "from importlib.metadata import distribution; "
                    f"ep=next(e for e in distribution('vigovbot').entry_points if e.name=={entrypoint!r}); "
                    "ep.load()()"
                )
                subprocess.run([sys.executable, "-c", invocation, *command, "--help"],
                               cwd=work, env=env, check=True)


if __name__ == "__main__":
    main()
