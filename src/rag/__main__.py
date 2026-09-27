"""Compatibility shim; implementation: vigovbot.rag.__main__."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.rag.__main__")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
