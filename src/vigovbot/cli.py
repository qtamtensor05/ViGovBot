"""Single public CLI with lazy imports for independent environments."""

import argparse
import sys
from vigovbot.console import configure_console


def main(argv=None):
    configure_console()
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="vigovbot", description="ViGovBot research pipelines")
    parser.add_argument("command", choices=["ingest", "embed", "merge", "rag"])
    if not argv or argv[0] in ("-h", "--help"):
        parser.print_help()
        return 0
    command = parser.parse_args(argv[:1]).command
    if command == "ingest":
        from vigovbot.pipelines.indexing import main as entry
    elif command == "embed":
        from vigovbot.embeddings.pack_worker import main as entry
    elif command == "merge":
        from vigovbot.vectordb.merge import main as entry
    else:
        from vigovbot.rag.__main__ import main as entry
    return entry(argv[1:])
