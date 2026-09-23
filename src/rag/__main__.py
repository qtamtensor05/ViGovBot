"""python -m src.rag --config rag_config.yaml run"""
import argparse
import json
import logging

from src.rag.config import load_config


def main(argv=None):
    parser = argparse.ArgumentParser(description="Qwen + RAG: unified/SQLite/FAISS và đánh giá qa_test")
    parser.add_argument("--config", default="rag_config.yaml", help="Đường dẫn cấu hình YAML")
    parser.add_argument("command", choices=["prepare", "smoke", "evaluate", "report", "run"], nargs="?", default="run")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    from src.rag.pipeline import execute
    result = execute(load_config(args.config), args.command)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
