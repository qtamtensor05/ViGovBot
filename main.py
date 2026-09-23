import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "rag":
        from src.rag.__main__ import main as rag_main
        return rag_main(sys.argv[2:])
    from src.ingestion.parse import main as ingestion_main
    return ingestion_main()


if __name__ == "__main__":
    raise SystemExit(main())
