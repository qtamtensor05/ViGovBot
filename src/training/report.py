"""Installed compatibility alias for vigovbot.training.report."""

import sys

from vigovbot.training import report as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
