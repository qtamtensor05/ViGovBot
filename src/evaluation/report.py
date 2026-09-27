"""Compatibility shim; implementation: vigovbot.evaluation.report."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.evaluation.report")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
