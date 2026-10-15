"""Installed compatibility alias for vigovbot.training.parameters."""

import sys

from vigovbot.training import parameters as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
