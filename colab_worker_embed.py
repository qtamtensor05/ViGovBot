"""Compatibility entry point; implementation lives in src.embeddings.pack_worker."""
import sys
from src.embeddings import pack_worker as implementation

if __name__ == "__main__":
    implementation.main()
else:
    sys.modules[__name__] = implementation
