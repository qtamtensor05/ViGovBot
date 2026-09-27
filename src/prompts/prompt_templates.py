"""Compatibility shim; implementation: vigovbot.prompts.prompt_templates."""
import sys
from importlib import import_module

implementation = import_module("vigovbot.prompts.prompt_templates")
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
