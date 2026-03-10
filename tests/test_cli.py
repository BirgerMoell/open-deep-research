import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from open_deep_research.cli import _emit_plan_result, _emit_research_result, _resolve_question, build_parser
from open_deep_research.models import ResearchResult, SearchPlan


class CliTests(unittest.TestCase):
    def test_resolve_question_from_positional(self):
        parser = build_parser()
        args = parser.parse_args(["research", "What is dense retrieval?"])
        self.assertEqual(_resolve_question(args, parser), "What is dense retrieval?")

    def test_resolve_question_from_file(self):
        parser = build_parser()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "question.txt"
            path.write_text("Question from file", encoding="utf-8")
            args = parser.parse_args(["plan", "--question-file", str(path)])
            self.assertEqual(_resolve_question(args, parser), "Question from file")

    def test_resolve_question_from_stdin(self):
        parser = build_parser()
        args = parser.parse_args(["plan", "--stdin"])
        with mock.patch("sys.stdin", io.StringIO("Question from stdin")):
            self.assertEqual(_resolve_question(args, parser), "Question from stdin")

    def test_emit_plan_queries(self):
        plan = SearchPlan(question="Q", search_queries=["a", "b"])
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            _emit_plan_result(plan, "queries")
        self.assertEqual(buffer.getvalue().strip().splitlines(), ["a", "b"])

    def test_emit_research_paths(self):
        result = ResearchResult(
            question="Q",
            output_dir="/tmp/out",
            report_path="/tmp/out/report.md",
            papers_path="/tmp/out/papers.json",
            trace_path="/tmp/out/trace.json",
            papers=[],
            plan=SearchPlan(question="Q", search_queries=["a"]),
        )
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            _emit_research_result(result, "paths")
        self.assertIn('"report_path": "/tmp/out/report.md"', buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
