from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class Settings:
    project_root: Path
    output_root: Path
    openalex_base_url: str
    openalex_mailto: Optional[str]
    openalex_api_key: Optional[str]
    openalex_timeout_sec: int
    seed_results_per_query: int
    max_reference_expansion: int
    max_citing_expansion: int
    llm_base_url: str
    llm_api_key: Optional[str]
    llm_model: str
    llm_timeout_sec: int

    @property
    def llm_enabled(self) -> bool:
        if not self.llm_base_url:
            return False
        if self.llm_base_url.startswith("https://api.openai.com") and not self.llm_api_key:
            return False
        return True

    @classmethod
    def from_env(cls, project_root: Path) -> "Settings":
        load_dotenv(project_root / ".env")
        output_root = project_root / "outputs"
        output_root.mkdir(parents=True, exist_ok=True)
        return cls(
            project_root=project_root,
            output_root=output_root,
            openalex_base_url=os.getenv("OPENALEX_BASE_URL", "https://api.openalex.org"),
            openalex_mailto=os.getenv("OPENALEX_MAILTO"),
            openalex_api_key=os.getenv("OPENALEX_API_KEY"),
            openalex_timeout_sec=int(os.getenv("OPENALEX_TIMEOUT_SEC", "30")),
            seed_results_per_query=int(os.getenv("OPENALEX_SEED_RESULTS_PER_QUERY", "12")),
            max_reference_expansion=int(os.getenv("OPENALEX_MAX_REFERENCE_EXPANSION", "5")),
            max_citing_expansion=int(os.getenv("OPENALEX_MAX_CITING_EXPANSION", "5")),
            llm_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            llm_api_key=os.getenv("OPENAI_API_KEY"),
            llm_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            llm_timeout_sec=int(os.getenv("OPENAI_TIMEOUT_SEC", "60")),
        )

