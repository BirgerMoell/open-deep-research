from __future__ import annotations

import re
from typing import List

from .llm import LLMClient
from .models import SearchPlan


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "do",
    "for",
    "how",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "why",
    "with",
}

SYNONYM_HINTS = {
    "citation": ["citation network", "citation graph"],
    "citations": ["citation network", "citation graph"],
    "graph": ["network"],
    "graphs": ["network"],
    "research": ["scholarly literature"],
    "papers": ["scholarly papers"],
    "source": ["paper discovery"],
    "sources": ["paper discovery"],
}


def _keyword_terms(question: str) -> List[str]:
    terms = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", question.lower())
    deduped = []
    for term in terms:
        if term in STOPWORDS or term in deduped:
            continue
        deduped.append(term)
    return deduped


def _fallback_plan(question: str) -> SearchPlan:
    terms = _keyword_terms(question)
    compressed = " ".join(terms[:7]) if terms else question
    search_queries = [question]
    if compressed and compressed != question:
        search_queries.append(compressed)
    if compressed:
        search_queries.append(f"{compressed} survey")
        search_queries.append(f"{compressed} review")
    enriched = []
    for term in terms[:6]:
        enriched.extend(SYNONYM_HINTS.get(term, []))
    if enriched:
        search_queries.append(" ".join((terms[:4] + enriched[:2])[:6]))
    if {"citation", "graph"}.issubset(set(terms)) or {"citations", "graphs"}.issubset(set(terms)):
        search_queries.append("scientific literature citation graph retrieval")
    deduped = []
    for query in search_queries:
        if query not in deduped:
            deduped.append(query)
    return SearchPlan(
        question=question,
        search_queries=deduped[:4],
        include_terms=terms[:8],
        notes="Fallback keyword plan without LLM assistance.",
    )


def build_plan(question: str, llm: LLMClient, force_no_llm: bool = False) -> SearchPlan:
    if force_no_llm or not llm.enabled:
        return _fallback_plan(question)

    system_prompt = (
        "You are planning a scholarly literature search. Return valid JSON only. "
        "Produce 4-6 search queries suitable for OpenAlex, concise inclusion terms, "
        "concise exclusion terms, optional year range, and a short note."
    )
    user_prompt = f"""
Question: {question}

Return JSON with exactly these keys:
- search_queries: array of strings
- include_terms: array of strings
- exclude_terms: array of strings
- year_start: integer or null
- year_end: integer or null
- notes: string
"""
    payload = llm.generate_json(system_prompt, user_prompt)
    if not payload:
        return _fallback_plan(question)

    queries = [str(item).strip() for item in payload.get("search_queries", []) if str(item).strip()]
    if not queries:
        return _fallback_plan(question)

    return SearchPlan(
        question=question,
        search_queries=queries[:6],
        include_terms=[str(item).strip() for item in payload.get("include_terms", []) if str(item).strip()],
        exclude_terms=[str(item).strip() for item in payload.get("exclude_terms", []) if str(item).strip()],
        year_start=int(payload["year_start"]) if payload.get("year_start") not in (None, "") else None,
        year_end=int(payload["year_end"]) if payload.get("year_end") not in (None, "") else None,
        notes=str(payload.get("notes", "")).strip(),
    )
