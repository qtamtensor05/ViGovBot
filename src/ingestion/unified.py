"""Compatibility shim; implementation: vigovbot.ingestion.unified."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.ingestion.unified")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
