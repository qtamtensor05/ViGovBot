"""Compatibility shim; implementation: vigovbot.embeddings.pack_worker."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.embeddings.pack_worker")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
