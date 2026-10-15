"""Compatibility alias for vigovbot.training.config."""

import sys

from vigovbot.training import config as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
