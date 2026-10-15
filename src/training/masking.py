"""Installed compatibility alias for vigovbot.training.masking."""

import sys

from vigovbot.training import masking as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
