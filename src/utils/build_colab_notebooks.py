"""Compatibility shim; implementation: vigovbot.utils.build_colab_notebooks."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.utils.build_colab_notebooks")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
