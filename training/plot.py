"""Compatibility alias for vigovbot.training.plot."""

import sys

from vigovbot.training import plot as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
