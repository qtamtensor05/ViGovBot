"""Installed compatibility alias for vigovbot.training.resume_verification."""

import sys

from vigovbot.training import resume_verification as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
