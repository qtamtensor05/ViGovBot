"""Compatibility alias for vigovbot.training.gpu_diagnostics."""

import sys

from vigovbot.training import gpu_diagnostics as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
