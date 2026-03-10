from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from typing import Dict, Iterable, List, Optional

from .config import Settings
from .models import Paper


SELECT_FIELDS = ",".join(
    [
        "id",
        "doi",
        "title",
        "publication_year",
        "authorships",
        "abstract_inverted_index",
        "best_oa_location",
        "primary_location",
        "referenced_works",
        "cited_by_api_url",
        "cited_by_count",
        "topics",
        "related_works",
    ]
)


def inverted_index_to_text(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    if not inverted_index:
        return ""
    max_position = -1
    for positions in inverted_index.values():
        for pos in positions:
            if pos > max_position:
                max_position = pos
    if max_position < 0:
        return ""
    words = [""] * (max_position + 1)
    for token, positions in inverted_index.items():
        for pos in positions:
            words[pos] = token
    return " ".join(word for word in words if word).replace(" ,", ",").replace(" .", ".")


def normalize_openalex_id(value: str) -> str:
    if value.startswith("https://openalex.org/"):
        return value.rsplit("/", 1)[-1]
    return value


def score_candidate(paper: Paper, question_terms: List[str], support_count: int) -> float:
    title_text = paper.title.lower()
    abstract_text = paper.abstract.lower()
    topic_text = " ".join(paper.topics).lower()
    title_hits = sum(1 for term in question_terms if term in title_text)
    abstract_hits = sum(1 for term in question_terms if term in abstract_text)
    topic_hits = sum(1 for term in question_terms if term in topic_text)
    lexical = ((0.65 * title_hits) + (0.25 * abstract_hits) + (0.10 * topic_hits)) / max(1, len(question_terms))
    citations = min(math.log1p(max(0, paper.cited_by_count)) / 8.0, 1.0)
    year_bonus = 0.0
    if paper.year:
        year_bonus = min(max(paper.year - 2015, 0) / 12.0, 1.0)
    support = min(support_count / 3.0, 1.0)
    lexical_gate = 1.0
    if title_hits == 0 and (abstract_hits + topic_hits) < 2:
        lexical_gate = 0.35
    return round((((0.62 * lexical) + (0.18 * citations) + (0.12 * support) + (0.08 * year_bonus)) * lexical_gate), 4)


class OpenAlexClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _request_json(self, url_or_path: str, params: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
            parsed = urllib.parse.urlparse(url_or_path)
            query = dict(urllib.parse.parse_qsl(parsed.query))
            if params:
                for key, value in params.items():
                    query[str(key)] = str(value)
            if self.settings.openalex_mailto and "mailto" not in query:
                query["mailto"] = self.settings.openalex_mailto
            if self.settings.openalex_api_key and "api_key" not in query:
                query["api_key"] = self.settings.openalex_api_key
            rebuilt = parsed._replace(query=urllib.parse.urlencode(query))
            url = urllib.parse.urlunparse(rebuilt)
        else:
            params = params or {}
            if self.settings.openalex_mailto:
                params.setdefault("mailto", self.settings.openalex_mailto)
            if self.settings.openalex_api_key:
                params.setdefault("api_key", self.settings.openalex_api_key)
            query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            url = f"{self.settings.openalex_base_url.rstrip('/')}/{url_or_path.lstrip('/')}"
            if query:
                url = f"{url}?{query}"

        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "open-deep-research/0.1",
            },
        )
        with urllib.request.urlopen(request, timeout=self.settings.openalex_timeout_sec) as response:
            return json.loads(response.read().decode("utf-8"))

    def _paper_from_result(self, item: Dict[str, object]) -> Paper:
        best_oa = item.get("best_oa_location") or {}
        primary = item.get("primary_location") or {}
        location = best_oa or primary
        source = location.get("source") or {}
        return Paper(
            id=str(item.get("id", "")),
            openalex_id=normalize_openalex_id(str(item.get("id", ""))),
            doi=item.get("doi"),
            title=str(item.get("title") or "").strip(),
            year=item.get("publication_year"),
            authors=[
                authorship.get("author", {}).get("display_name", "")
                for authorship in item.get("authorships", [])
                if authorship.get("author", {}).get("display_name")
            ],
            abstract=inverted_index_to_text(item.get("abstract_inverted_index")),
            cited_by_count=int(item.get("cited_by_count") or 0),
            topics=[
                topic.get("display_name", "")
                for topic in item.get("topics", [])
                if topic.get("display_name")
            ],
            landing_page_url=location.get("landing_page_url"),
            pdf_url=location.get("pdf_url"),
            source_name=source.get("display_name") or location.get("raw_source_name"),
            referenced_work_ids=[normalize_openalex_id(value) for value in item.get("referenced_works", [])],
            cited_by_api_url=item.get("cited_by_api_url"),
            is_oa=bool(location.get("is_oa")),
        )

    def search_works(self, query: str, per_page: Optional[int] = None) -> List[Paper]:
        data = self._request_json(
            "works",
            params={
                "search": query,
                "per-page": per_page or self.settings.seed_results_per_query,
                "select": SELECT_FIELDS,
            },
        )
        return [self._paper_from_result(item) for item in data.get("results", [])]

    def get_work(self, work_id: str) -> Paper:
        data = self._request_json(
            f"works/{normalize_openalex_id(work_id)}",
            params={"select": SELECT_FIELDS},
        )
        return self._paper_from_result(data)

    def get_works(self, work_ids: Iterable[str]) -> List[Paper]:
        papers: List[Paper] = []
        for work_id in work_ids:
            try:
                papers.append(self.get_work(work_id))
            except Exception:
                continue
        return papers

    def get_citing_works(self, cited_by_api_url: Optional[str], per_page: int) -> List[Paper]:
        if not cited_by_api_url:
            return []
        data = self._request_json(
            cited_by_api_url,
            params={"per-page": per_page, "select": SELECT_FIELDS},
        )
        return [self._paper_from_result(item) for item in data.get("results", [])]
