"""Compatibility entry point; implementation lives in src.vectordb.merge."""
import sys
from src.vectordb import merge as implementation

if __name__ == "__main__":
    implementation.main()
else:
    sys.modules[__name__] = implementation
