"""Installed compatibility alias for vigovbot.training.control_cli."""

import sys

from vigovbot.training import control_cli as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
