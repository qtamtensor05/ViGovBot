"""Compatibility shim; implementation: vigovbot.vectordb.vector_store."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.vectordb.vector_store")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
