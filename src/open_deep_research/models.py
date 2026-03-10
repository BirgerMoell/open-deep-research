from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


@dataclass
class SearchPlan:
    question: str
    search_queries: List[str]
    include_terms: List[str] = field(default_factory=list)
    exclude_terms: List[str] = field(default_factory=list)
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class Paper:
    id: str
    openalex_id: str
    doi: Optional[str]
    title: str
    year: Optional[int]
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    cited_by_count: int = 0
    topics: List[str] = field(default_factory=list)
    landing_page_url: Optional[str] = None
    pdf_url: Optional[str] = None
    source_name: Optional[str] = None
    referenced_work_ids: List[str] = field(default_factory=list)
    cited_by_api_url: Optional[str] = None
    is_oa: bool = False
    fetched_text: str = ""
    fetched_from: Optional[str] = None
    score: float = 0.0
    selection_reason: str = ""
    evidence_label: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class ResearchResult:
    question: str
    output_dir: str
    report_path: str
    papers_path: str
    trace_path: str
    papers: List[Paper]
    plan: SearchPlan

    def to_dict(self) -> Dict[str, object]:
        return {
            "question": self.question,
            "output_dir": self.output_dir,
            "report_path": self.report_path,
            "papers_path": self.papers_path,
            "trace_path": self.trace_path,
            "plan": self.plan.to_dict(),
            "papers": [paper.to_dict() for paper in self.papers],
        }

