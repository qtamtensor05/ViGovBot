"""Compatibility namespace for older checkouts and notebooks."""
import sys
from pathlib import Path

_source = str(Path(__file__).resolve().parent)
if _source not in sys.path:
    sys.path.insert(0, _source)
