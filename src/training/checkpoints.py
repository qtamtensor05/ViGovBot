"""Installed compatibility alias for vigovbot.training.checkpoints."""

import sys

from vigovbot.training import checkpoints as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
