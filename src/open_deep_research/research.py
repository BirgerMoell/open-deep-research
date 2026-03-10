from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from .config import Settings
from .fetchers import fetch_open_text
from .llm import LLMClient
from .models import Paper, ResearchResult
from .openalex import OpenAlexClient, score_candidate
from .planner import build_plan
from .reporting import synthesize_report, trace_payload


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:80] or "research-run"


def _question_terms(question: str, include_terms: List[str]) -> List[str]:
    terms = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", question.lower())
    deduped: List[str] = []
    for term in terms + [term.lower() for term in include_terms]:
        if term not in deduped:
            deduped.append(term)
    return deduped[:12]


def _apply_filters(papers: List[Paper], year_start, year_end, exclude_terms: List[str]) -> List[Paper]:
    kept = []
    lowered_exclusions = [term.lower() for term in exclude_terms]
    for paper in papers:
        if year_start and paper.year and paper.year < year_start:
            continue
        if year_end and paper.year and paper.year > year_end:
            continue
        haystack = " ".join([paper.title, paper.abstract]).lower()
        if any(term in haystack for term in lowered_exclusions):
            continue
        kept.append(paper)
    return kept


class DeepResearchEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.openalex = OpenAlexClient(settings)
        self.llm = LLMClient(settings)

    def _rerank_with_llm(self, question: str, papers: List[Paper]) -> Dict[str, str]:
        if not self.llm.enabled or not papers:
            return {}

        compact = []
        for paper in papers[:15]:
            compact.append(
                {
                    "id": paper.openalex_id,
                    "title": paper.title,
                    "year": paper.year,
                    "citations": paper.cited_by_count,
                    "topics": paper.topics[:5],
                    "abstract": paper.abstract[:600],
                }
            )
        payload = self.llm.generate_json(
            "You rank scholarly papers for relevance. Return valid JSON only.",
            (
                f"Question: {question}\n\n"
                "Return JSON with a single key named selected. "
                "Its value must be an array of objects with keys id and reason. "
                "Select the strongest papers for answering the question.\n\n"
                f"Papers: {json.dumps(compact)}"
            ),
        )
        if not payload:
            return {}
        selected = payload.get("selected", [])
        reasons = {}
        if isinstance(selected, list):
            for item in selected:
                if not isinstance(item, dict):
                    continue
                if item.get("id"):
                    reasons[str(item["id"])] = str(item.get("reason", "")).strip()
        return reasons

    def run(
        self,
        question: str,
        *,
        output_dir: Path | None = None,
        final_papers: int = 8,
        no_llm: bool = False,
    ) -> ResearchResult:
        use_llm = self.llm.enabled and not no_llm
        plan = build_plan(question, self.llm, force_no_llm=not use_llm)
        target_dir = output_dir or (self.settings.output_root / slugify(question))
        target_dir.mkdir(parents=True, exist_ok=True)

        trace: Dict[str, object] = {"queries": [], "expansions": []}
        candidate_by_id: Dict[str, Paper] = {}
        support_counts = defaultdict(int)
        question_terms = _question_terms(question, plan.include_terms)

        for query in plan.search_queries:
            results = self.openalex.search_works(query, per_page=self.settings.seed_results_per_query)
            trace["queries"].append({"query": query, "count": len(results)})
            filtered = _apply_filters(results, plan.year_start, plan.year_end, plan.exclude_terms)
            for paper in filtered:
                candidate_by_id.setdefault(paper.openalex_id, paper)
                support_counts[paper.openalex_id] += 1

        seeds = list(candidate_by_id.values())
        for paper in seeds:
            paper.score = score_candidate(paper, question_terms, support_counts[paper.openalex_id])
            paper.selection_reason = "Direct OpenAlex search hit."
        seeds.sort(key=lambda paper: paper.score, reverse=True)
        top_seeds = seeds[: max(final_papers, 5)]

        for seed in top_seeds:
            referenced = self.openalex.get_works(seed.referenced_work_ids[: self.settings.max_reference_expansion])
            citing = self.openalex.get_citing_works(seed.cited_by_api_url, self.settings.max_citing_expansion)
            trace["expansions"].append(
                {
                    "seed": seed.openalex_id,
                    "references_added": len(referenced),
                    "citing_added": len(citing),
                }
            )
            for paper in referenced + citing:
                existing = candidate_by_id.get(paper.openalex_id)
                if existing is None:
                    candidate_by_id[paper.openalex_id] = paper
                support_counts[paper.openalex_id] += 1

        candidates = _apply_filters(list(candidate_by_id.values()), plan.year_start, plan.year_end, plan.exclude_terms)
        for paper in candidates:
            paper.score = score_candidate(paper, question_terms, support_counts[paper.openalex_id])
            if support_counts[paper.openalex_id] > 1 and paper.selection_reason != "Direct OpenAlex search hit.":
                paper.selection_reason = "Found through multiple search or expansion paths."
            elif not paper.selection_reason:
                paper.selection_reason = "Found through OpenAlex citation expansion."

        candidates.sort(key=lambda paper: paper.score, reverse=True)
        llm_reasons = self._rerank_with_llm(question, candidates) if use_llm else {}

        if llm_reasons:
            for paper in candidates:
                if paper.openalex_id in llm_reasons:
                    paper.score += 0.15
                    paper.selection_reason = llm_reasons[paper.openalex_id] or "LLM reranking selected this paper."
            candidates.sort(key=lambda paper: paper.score, reverse=True)

        selected = candidates[:final_papers]
        for index, paper in enumerate(selected, start=1):
            paper.evidence_label = f"P{index}"
            fetched_text, fetched_from = fetch_open_text(paper)
            paper.fetched_text = fetched_text
            paper.fetched_from = fetched_from
            if fetched_text and fetched_from:
                paper.selection_reason = f"{paper.selection_reason} Open text fetched from {fetched_from}."

        report = synthesize_report(question, plan, selected, self.llm if use_llm else None)

        report_path = target_dir / "report.md"
        papers_path = target_dir / "papers.json"
        trace_path = target_dir / "trace.json"
        report_path.write_text(report, encoding="utf-8")
        papers_path.write_text(
            json.dumps([paper.to_dict() for paper in selected], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        trace_path.write_text(
            json.dumps(trace_payload(plan, question, trace, selected), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return ResearchResult(
            question=question,
            output_dir=str(target_dir),
            report_path=str(report_path),
            papers_path=str(papers_path),
            trace_path=str(trace_path),
            papers=selected,
            plan=plan,
        )
