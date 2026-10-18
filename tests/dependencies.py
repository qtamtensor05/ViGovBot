"""Explicit missing-dependency skips; never hide internal import failures."""
import unittest
import importlib
from functools import wraps

DEPENDENCIES = frozenset({
    "faiss", "pydantic", "filelock", "numpy", "typer", "yaml", "psutil",
    "huggingface_hub", "requests", "tqdm", "ijson", "pandas", "matplotlib",
    "nltk", "rouge_score", "sacrebleu", "torch", "transformers", "peft",
    "datasets", "accelerate", "safetensors", "sentence_transformers",
})


def skip_missing_dependency(error):
    if error.name not in DEPENDENCIES:
        raise error
    raise unittest.SkipTest(f"Missing test dependency: {error.name}; install .[test,dev] (GPU tests need .[gpu])") from error


def requires_dependencies(*names):
    """Check deferred metric/tensor dependencies before executing a test."""
    def decorate(function):
        @wraps(function)
        def run(*args, **kwargs):
            for name in names:
                try:
                    importlib.import_module(name)
                except ModuleNotFoundError as error:
                    skip_missing_dependency(error)
            return function(*args, **kwargs)
        return run
    return decorate
