"""Compatibility shim; implementation: vigovbot.chunking.markdown."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.chunking.markdown")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
