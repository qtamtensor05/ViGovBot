"""Compatibility alias for vigovbot.training.evaluate."""

import sys

from vigovbot.training import evaluate as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
