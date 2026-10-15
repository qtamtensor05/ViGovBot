"""Installed compatibility alias for vigovbot.training.early_stopping."""

import sys

from vigovbot.training import early_stopping as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
