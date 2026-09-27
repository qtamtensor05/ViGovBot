"""Compatibility shim; implementation: vigovbot.embeddings.embedder."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.embeddings.embedder")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
