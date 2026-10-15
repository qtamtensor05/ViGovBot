"""Compatibility alias for vigovbot.training.preflight."""

import sys

from vigovbot.training import preflight as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
