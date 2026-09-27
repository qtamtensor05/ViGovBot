"""Compatibility shim; implementation: vigovbot.utils.colab_runtime."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.utils.colab_runtime")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
