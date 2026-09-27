"""python -m src.rag --config rag_config.yaml run"""

import argparse
import json
import logging

from vigovbot.rag.config import load_config
from vigovbot.console import configure_console


def main(argv=None):
    configure_console()
    parser = argparse.ArgumentParser(description="Qwen + RAG: unified/SQLite/FAISS và đánh giá qa_test")
    parser.add_argument("--config", default="rag_config.yaml", help="Đường dẫn cấu hình YAML")
    parser.add_argument(
        "command", choices=["prepare", "ask", "smoke", "evaluate", "report", "run"], nargs="?", default="run"
    )
    parser.add_argument("--question", help="Question for the ask command; no evaluation dataset required")
    args = parser.parse_args(argv)
    if args.command == "ask" and not (args.question and args.question.strip()):
        parser.error("ask requires a nonempty --question")
    if args.command != "ask" and args.question is not None:
        parser.error("--question is only valid with ask")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    from vigovbot.rag.pipeline import execute

    if args.command == "ask":
        result = execute(load_config(args.config), args.command, question=args.question)
    else:
        result = execute(load_config(args.config), args.command)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
