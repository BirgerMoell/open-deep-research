from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .api import serve
from .config import Settings
from .planner import build_plan
from .research import DeepResearchEngine


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _add_question_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("question", nargs="?", help="Research question, or '-' to read from stdin")
    parser.add_argument("--stdin", action="store_true", help="Read the question from stdin")
    parser.add_argument("--question-file", type=Path, help="Read the question from a file")


def _resolve_question(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    sources = 0
    if getattr(args, "question", None) and args.question != "-":
        sources += 1
    if getattr(args, "stdin", False) or getattr(args, "question", None) == "-":
        sources += 1
    if getattr(args, "question_file", None):
        sources += 1

    if sources == 0:
        parser.error("A question is required. Pass it as an argument, --stdin, or --question-file.")
    if sources > 1:
        parser.error("Use exactly one question source: positional question, --stdin, or --question-file.")

    if getattr(args, "question_file", None):
        question = args.question_file.read_text(encoding="utf-8").strip()
    elif getattr(args, "stdin", False) or getattr(args, "question", None) == "-":
        question = sys.stdin.read().strip()
    else:
        question = str(args.question).strip()

    if not question:
        parser.error("The resolved question is empty.")
    return question


def _emit_research_result(result, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return
    if output_format == "paths":
        print(
            json.dumps(
                {
                    "output_dir": result.output_dir,
                    "report_path": result.report_path,
                    "papers_path": result.papers_path,
                    "trace_path": result.trace_path,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    if output_format == "report":
        print(Path(result.report_path).read_text(encoding="utf-8"))
        return
    if output_format == "papers":
        print(Path(result.papers_path).read_text(encoding="utf-8"))
        return
    if output_format == "trace":
        print(Path(result.trace_path).read_text(encoding="utf-8"))
        return
    raise ValueError(f"Unsupported output format: {output_format}")


def _emit_plan_result(plan, output_format: str) -> None:
    payload = json.dumps(plan.to_dict(), indent=2, ensure_ascii=False)
    if output_format == "json":
        print(payload)
        return
    if output_format == "queries":
        for query in plan.search_queries:
            print(query)
        return
    raise ValueError(f"Unsupported output format: {output_format}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open Deep Research")
    subparsers = parser.add_subparsers(dest="command", required=True)

    research = subparsers.add_parser("research", help="Run a deep research job")
    _add_question_arguments(research)
    research.add_argument("--output-dir", type=Path, help="Write outputs to this directory")
    research.add_argument("--final-papers", type=int, default=8, help="Number of final papers to keep")
    research.add_argument("--no-llm", action="store_true", help="Disable LLM planning and synthesis")
    research.add_argument(
        "--format",
        choices=["json", "paths", "report", "papers", "trace"],
        default="json",
        help="What to print to stdout after the run completes",
    )

    plan = subparsers.add_parser("plan", help="Show the query plan")
    _add_question_arguments(plan)
    plan.add_argument("--no-llm", action="store_true", help="Disable LLM planning")
    plan.add_argument(
        "--format",
        choices=["json", "queries"],
        default="json",
        help="What to print to stdout",
    )

    serve_cmd = subparsers.add_parser("serve", help="Run the local HTTP API")
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8080)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = Settings.from_env(_project_root())

    if args.command == "research":
        question = _resolve_question(args, parser)
        engine = DeepResearchEngine(settings)
        result = engine.run(
            question,
            output_dir=args.output_dir,
            final_papers=args.final_papers,
            no_llm=args.no_llm,
        )
        _emit_research_result(result, args.format)
        return

    if args.command == "plan":
        from .llm import LLMClient

        question = _resolve_question(args, parser)
        plan = build_plan(question, LLMClient(settings), force_no_llm=args.no_llm)
        _emit_plan_result(plan, args.format)
        return

    if args.command == "serve":
        serve(settings, args.host, args.port)
        return

    parser.error("Unknown command")


if __name__ == "__main__":
    main()
