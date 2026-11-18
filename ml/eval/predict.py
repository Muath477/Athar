import argparse
import json
import os
import time
from pathlib import Path

from ml.serve.client import DEFAULT_MODEL, DEFAULT_TIMEOUT_S, DEFAULT_URL, ChatEndpoint

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a served model to map every test wall")
    parser.add_argument("--test", type=Path, default=DATA_DIR / "build" / "test.jsonl")
    parser.add_argument("--out", type=Path, default=Path("ml/eval/predictions.jsonl"))
    parser.add_argument("--url", default=os.environ.get("SADU_QWEN_URL", DEFAULT_URL))
    parser.add_argument("--model", default=os.environ.get("SADU_QWEN_MODEL", DEFAULT_MODEL))
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    args = parser.parse_args()
    endpoint = ChatEndpoint(args.url, args.model, args.timeout, os.environ.get("SADU_QWEN_TOKEN"))
    rows = [json.loads(line) for line in args.test.read_text().splitlines() if line.strip()]
    with args.out.open("w") as out:
        for row in rows:
            if row["task"] != "wall_map":
                continue
            image = next(p["image"] for p in row["messages"][1]["content"] if p["type"] == "image")
            started = time.monotonic()
            answer = endpoint.map_wall((DATA_DIR / image).read_bytes())
            seconds = round(time.monotonic() - started, 2)
            out.write(
                json.dumps({"id": row["id"], "answer": answer, "seconds": seconds}, ensure_ascii=False) + "\n"
            )
            print(f"{row['id']}: {seconds}s")


if __name__ == "__main__":
    main()
