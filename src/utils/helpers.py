"""Compatibility shim; implementation: vigovbot.utils.helpers."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.utils.helpers")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
