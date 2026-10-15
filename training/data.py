"""Compatibility alias for vigovbot.training.data."""

import sys

from vigovbot.training import data as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
