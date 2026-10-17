"""Repository entry point for the unified CLI; no implicit ingestion."""

import sys


def main():
    from vigovbot.cli.main import main as cli_main
    return cli_main(sys.argv[1:] or ["--help"])


if __name__ == "__main__":
    raise SystemExit(main())
