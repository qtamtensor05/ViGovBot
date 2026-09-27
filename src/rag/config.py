"""Compatibility shim; implementation: vigovbot.rag.config."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.rag.config")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
