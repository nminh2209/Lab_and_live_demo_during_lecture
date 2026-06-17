from __future__ import annotations

import argparse
from pathlib import Path

from app.config import Settings
from app.graph import ShoppingAssistant
from app.utils import dump_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VinShop multi-agent shopping assistant.")
    parser.add_argument("--question", help="Run one question through the graph.")
    parser.add_argument("--test-file", default="data/test.json")
    parser.add_argument("--trace-file", default=None)
    parser.add_argument("--output-dir", default="src/artifacts/traces")
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--rebuild-index", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.load()
    assistant = ShoppingAssistant(settings=settings)

    if args.batch:
        test_file = Path(args.test_file)
        if not test_file.is_absolute():
            test_file = settings.root_dir / test_file
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = settings.root_dir / output_dir
        summary = assistant.run_batch(
            test_file=test_file,
            output_dir=output_dir,
            rebuild_index=args.rebuild_index,
        )
        print(dump_json(summary))
        return

    if not args.question:
        raise SystemExit("Provide --question or use --batch.")

    trace_file = Path(args.trace_file) if args.trace_file else None
    if trace_file is not None and not trace_file.is_absolute():
        trace_file = settings.root_dir / trace_file

    result = assistant.ask(
        question=args.question,
        trace_file=trace_file,
        rebuild_index=args.rebuild_index,
    )
    print(result["final_answer"])


if __name__ == "__main__":
    main()
