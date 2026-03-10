from __future__ import annotations

import argparse
import json
from pathlib import Path

from .api import serve
from .config import Settings
from .planner import build_plan
from .research import DeepResearchEngine


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open Deep Research")
    subparsers = parser.add_subparsers(dest="command", required=True)

    research = subparsers.add_parser("research", help="Run a deep research job")
    research.add_argument("question", help="Research question")
    research.add_argument("--output-dir", type=Path, help="Write outputs to this directory")
    research.add_argument("--final-papers", type=int, default=8, help="Number of final papers to keep")
    research.add_argument("--no-llm", action="store_true", help="Disable LLM planning and synthesis")

    plan = subparsers.add_parser("plan", help="Show the query plan")
    plan.add_argument("question", help="Research question")
    plan.add_argument("--no-llm", action="store_true", help="Disable LLM planning")

    serve_cmd = subparsers.add_parser("serve", help="Run the local HTTP API")
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8080)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = Settings.from_env(_project_root())

    if args.command == "research":
        engine = DeepResearchEngine(settings)
        result = engine.run(
            args.question,
            output_dir=args.output_dir,
            final_papers=args.final_papers,
            no_llm=args.no_llm,
        )
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return

    if args.command == "plan":
        from .llm import LLMClient

        plan = build_plan(args.question, LLMClient(settings), force_no_llm=args.no_llm)
        print(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))
        return

    if args.command == "serve":
        serve(settings, args.host, args.port)
        return

    parser.error("Unknown command")


if __name__ == "__main__":
    main()

