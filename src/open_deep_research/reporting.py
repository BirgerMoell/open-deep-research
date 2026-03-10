from __future__ import annotations

from typing import Dict, List

from .llm import LLMClient
from .models import Paper, SearchPlan


def _paper_reference(paper: Paper) -> str:
    authors = ", ".join(paper.authors[:3]) if paper.authors else "Unknown authors"
    year = str(paper.year) if paper.year else "n.d."
    doi = paper.doi or "No DOI"
    return f"- [{paper.evidence_label}] {authors} ({year}). {paper.title}. {doi}"


def _fallback_body(question: str, papers: List[Paper]) -> str:
    lines = [
        "## Executive Summary",
        f"The retrieval pipeline collected {len(papers)} papers relevant to: {question}",
        "",
        "## Key Papers",
    ]
    for paper in papers:
        abstract = paper.abstract[:500] + ("..." if len(paper.abstract) > 500 else "")
        lines.append(
            f"### {paper.evidence_label}: {paper.title}\n"
            f"- Year: {paper.year or 'unknown'}\n"
            f"- Citations: {paper.cited_by_count}\n"
            f"- Why selected: {paper.selection_reason or 'High heuristic score.'}\n"
            f"- Abstract: {abstract or 'No abstract available.'}"
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "- This fallback report was generated without LLM synthesis.",
            "- Interpret the paper list as a starting point for manual review.",
        ]
    )
    return "\n".join(lines)


def synthesize_report(question: str, plan: SearchPlan, papers: List[Paper], llm: LLMClient | None) -> str:
    bibliography = "\n".join(_paper_reference(paper) for paper in papers)

    if not llm or not llm.enabled:
        body = _fallback_body(question, papers)
        return f"{body}\n\n## Bibliography\n{bibliography}\n"

    evidence_blocks = []
    for paper in papers:
        snippet = paper.fetched_text or paper.abstract or "No textual evidence available."
        evidence_blocks.append(
            "\n".join(
                [
                    f"{paper.evidence_label}: {paper.title}",
                    f"Year: {paper.year or 'unknown'}",
                    f"Citations: {paper.cited_by_count}",
                    f"Topics: {', '.join(paper.topics[:5]) or 'n/a'}",
                    f"Selection reason: {paper.selection_reason or 'heuristic ranking'}",
                    f"Evidence snippet: {snippet[:1200]}",
                ]
            )
        )

    system_prompt = (
        "You are writing a concise scholarly literature review. "
        "Use only the supplied evidence. Cite claims with the provided labels such as [P1]. "
        "Do not invent papers. Write Markdown."
    )
    user_prompt = "\n\n".join(
        [
            f"Research question: {question}",
            f"Search notes: {plan.notes or 'No additional notes.'}",
            "Write these sections:",
            "1. Executive Summary",
            "2. Main Themes",
            "3. Methodological Patterns",
            "4. Gaps and Open Questions",
            "5. Suggested Next Searches",
            "",
            "Evidence:",
            "\n\n".join(evidence_blocks),
        ]
    )
    try:
        body = llm.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        ).strip()
    except Exception:
        body = ""
    if not body:
        body = _fallback_body(question, papers)

    return f"{body}\n\n## Bibliography\n{bibliography}\n"


def trace_payload(plan: SearchPlan, question: str, trace: Dict[str, object], papers: List[Paper]) -> Dict[str, object]:
    payload = dict(trace)
    payload["question"] = question
    payload["plan"] = plan.to_dict()
    payload["selected_papers"] = [paper.to_dict() for paper in papers]
    return payload
