"""Compatibility shim; implementation: vigovbot.ingestion.recovery."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.ingestion.recovery")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
