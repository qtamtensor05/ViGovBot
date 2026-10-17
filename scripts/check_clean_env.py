"""Install test extras or a chosen platform lock in an isolated venv and run tests."""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import venv


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, help="Optional lock for this interpreter/platform; otherwise resolve .[test,dev]")
    args = parser.parse_args()
    if args.lock and not args.lock.is_file():
        parser.error("Lock file does not exist")
    with tempfile.TemporaryDirectory(prefix="vigovbot-clean-") as work:
        venv.EnvBuilder(with_pip=True).create(work)
        python = Path(work) / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [str(python), "-m", "pip", "install", *(["-r", str(args.lock.resolve())] if args.lock else [str(root) + "[test,dev]"])],
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
