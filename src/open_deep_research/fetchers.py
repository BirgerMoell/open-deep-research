from __future__ import annotations

import io
import re
import urllib.request
from html.parser import HTMLParser
from typing import Optional, Tuple

from .models import Paper


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.fragments = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            cleaned = data.strip()
            if cleaned:
                self.fragments.append(cleaned)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.fragments)).strip()


def _extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""

    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages[:10]:
        pages.append(page.extract_text() or "")
    return re.sub(r"\s+", " ", " ".join(pages)).strip()


def fetch_open_text(paper: Paper, timeout_sec: int = 20, max_chars: int = 12000) -> Tuple[str, Optional[str]]:
    candidates = [paper.pdf_url, paper.landing_page_url]
    for url in candidates:
        if not url:
            continue
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "open-deep-research/0.1"})
            with urllib.request.urlopen(request, timeout=timeout_sec) as response:
                content_type = response.headers.get("Content-Type", "")
                body = response.read(8_000_000)
        except Exception:
            continue

        if "pdf" in content_type or url.lower().endswith(".pdf"):
            text = _extract_pdf_text(body)
            if text:
                return text[:max_chars], url
            continue

        if "html" in content_type or content_type.startswith("text/") or not content_type:
            parser = _TextExtractor()
            parser.feed(body.decode("utf-8", errors="ignore"))
            text = parser.text()
            if text:
                return text[:max_chars], url

    return "", None

