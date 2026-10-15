"""Compatibility alias for vigovbot.training.artifacts."""

import sys

from vigovbot.training import artifacts as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
