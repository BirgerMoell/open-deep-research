import unittest

from open_deep_research.openalex import inverted_index_to_text, normalize_openalex_id, score_candidate
from open_deep_research.planner import build_plan
from open_deep_research.llm import LLMClient
from open_deep_research.models import Paper


class FakeSettings:
    llm_base_url = ""
    llm_api_key = None

    @property
    def llm_enabled(self):
        return False


class CoreTests(unittest.TestCase):
    def test_inverted_index_to_text(self):
        value = {"hello": [0], "world": [1], "again": [2]}
        self.assertEqual(inverted_index_to_text(value), "hello world again")

    def test_normalize_openalex_id(self):
        self.assertEqual(normalize_openalex_id("https://openalex.org/W123"), "W123")
        self.assertEqual(normalize_openalex_id("W123"), "W123")

    def test_fallback_plan(self):
        plan = build_plan("How do deep research agents use citations?", LLMClient(FakeSettings()), force_no_llm=True)
        self.assertGreaterEqual(len(plan.search_queries), 1)
        self.assertIn("deep", " ".join(plan.include_terms))

    def test_score_candidate(self):
        paper = Paper(
            id="https://openalex.org/W123",
            openalex_id="W123",
            doi=None,
            title="Deep research with citation graphs",
            year=2024,
            abstract="This paper studies deep research systems and citation expansion.",
            cited_by_count=42,
        )
        score = score_candidate(paper, ["deep", "research", "citation"], 2)
        self.assertGreater(score, 0.0)


if __name__ == "__main__":
    unittest.main()

