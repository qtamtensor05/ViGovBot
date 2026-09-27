"""Compatibility alias for indexing orchestration."""

import sys
from vigovbot.pipelines import indexing

if __name__ == "__main__":
    raise SystemExit(indexing.main())
else:
    sys.modules[__name__] = indexing
