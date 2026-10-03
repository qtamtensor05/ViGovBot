"""Validate saved routing responses without rerunning model inference."""
import json
import sys
from pathlib import Path

from vigovbot.rag.routing import parse_route


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    path = Path(sys.argv[1])
    total = routed = retries = fallbacks = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        total += 1
        raw = row.get("raw_routing") or {}
        if not raw:
            continue
        routed += 1
        if "retry" not in raw:
            continue
        retries += 1
        fallback = raw.get("fallback_reason") == "invalid_routing_after_retry"
        fallbacks += int(fallback)
        print(f"line={line_number} fallback={fallback}")
        for attempt in ("initial", "retry"):
            text = raw.get(f"{attempt}_text", raw[attempt].get("message", {}).get("content", ""))
            try:
                json.loads(text)
                syntax = "valid"
            except ValueError:
                syntax = "invalid"
            try:
                # Nonempty history isolates schema errors from missing-history errors.
                parse_route(text, [{"role": "user", "content": "context"}])
                error = None
            except ValueError as exc:
                error = str(exc)
            print(json.dumps({"attempt": attempt, "json_syntax": syntax,
                              "validator_error": error, "saved_error": raw.get(f"{attempt}_error"),
                              "response": text}, ensure_ascii=False))
        print(json.dumps({"prediction": row.get("answer", row.get("prediction")),
                          "retrieval_query": row.get("retrieval_query"),
                          "telemetry": row.get("telemetry")}, ensure_ascii=False))
    print(json.dumps({"rows": total, "rows_with_raw_routing": routed,
                      "retries": retries, "fallbacks": fallbacks}))


if __name__ == "__main__":
    main()
