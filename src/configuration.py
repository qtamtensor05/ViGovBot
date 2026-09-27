"""Compatibility shim; implementation: vigovbot.configuration."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.configuration")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
