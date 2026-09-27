"""Compatibility shim; implementation: vigovbot.llm.llm_client."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.llm.llm_client")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
