"""Compatibility shim; implementation: vigovbot.evaluation.runner."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.evaluation.runner")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
