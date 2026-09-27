"""Legacy source-checkout notebook generation entry point."""

import runpy
from pathlib import Path


def main():
    runpy.run_path(str(Path(__file__).resolve().parents[3] / "scripts/build_colab_notebooks.py"), run_name="__main__")
