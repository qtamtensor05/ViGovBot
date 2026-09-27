"""Compatibility shim; implementation: vigovbot.ingestion.parse."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.ingestion.parse")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
