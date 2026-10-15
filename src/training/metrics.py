"""Installed compatibility alias for vigovbot.training.metrics."""

import sys

from vigovbot.training import metrics as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
