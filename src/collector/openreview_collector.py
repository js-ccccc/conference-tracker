"""OpenReview API 采集器"""

from __future__ import annotations

import logging
from typing import Any

from src.collector.base import BaseCollector
from src.models import Author, Conference, Paper

logger = logging.getLogger(__name__)


class OpenReviewCollector(BaseCollector):
    """通过 OpenReview API 获取录用论文列表"""

    def __init__(self, settings: dict[str, Any]):
        super().__init__(settings)
        self.api_bases = [
            settings.get("openreview", {}).get("api_base", "https://api2.openreview.net"),
            "https://api.openreview.net",
        ]
        self.batch_size = settings.get("openreview", {}).get("batch_size", 1000)
        self.session.headers.update({"Accept": "application/json"})

    @property
    def source_name(self) -> str:
        return "openreview"

    def collect(self, conference: Conference, source_config: dict) -> list[Paper]:
        if not source_config or not source_config.get("venue_id"):
            logger.info("No OpenReview venue_id for %s, skipping", conference.abbr)
            return []

        venue_id = source_config["venue_id"]
        papers: list[Paper] = []
        offset = 0

        while True:
            notes = self._fetch_notes(venue_id, offset)
            if not notes:
                break

            for note in notes:
                paper = self._parse_note(note)
                if paper:
                    papers.append(paper)

            if len(notes) < self.batch_size:
                break
            offset += self.batch_size

        logger.info(
            "OpenReview: collected %d papers for %s", len(papers), conference.abbr
        )
        return papers

    def _fetch_notes(self, venue_id: str, offset: int) -> list[dict]:
        params = {
            "content.venueid": venue_id,
            "limit": self.batch_size,
            "offset": offset,
        }
        for api_base in self.api_bases:
            url = f"{api_base}/notes"
            response = self.get(url, params=params)
            if response:
                data = response.json()
                return data.get("notes", [])
        return []

    def _parse_note(self, note: dict) -> Paper | None:
        content = note.get("content", {})
        title = content.get("title", "")
        if not title:
            return None

        if isinstance(title, dict):
            title = title.get("value", "")

        authors = self._parse_authors(content)
        abstract = content.get("abstract", "")
        if isinstance(abstract, dict):
            abstract = abstract.get("value", "")

        award = self._detect_award(content)
        paper_id = note.get("id", "")
        url = f"https://openreview.net/forum?id={paper_id}" if paper_id else None

        return Paper(
            title=title.strip(),
            authors=authors,
            abstract=abstract.strip() if abstract else None,
            url=url,
            award=award,
            source=self.source_name,
            paper_id=paper_id,
        )

    def _parse_authors(self, content: dict) -> list[Author]:
        authors: list[Author] = []

        author_names = content.get("authors", [])
        if isinstance(author_names, dict):
            author_names = author_names.get("value", [])

        affiliations_raw = content.get("authorids", content.get("affiliations", []))
        if isinstance(affiliations_raw, dict):
            affiliations_raw = affiliations_raw.get("value", [])

        affiliation_list = content.get("affiliations", [])
        if isinstance(affiliation_list, dict):
            affiliation_list = affiliation_list.get("value", [])

        for i, name in enumerate(author_names):
            affs: list[str] = []
            if i < len(affiliation_list):
                aff = affiliation_list[i]
                if isinstance(aff, str):
                    affs = [aff]
                elif isinstance(aff, list):
                    affs = [str(a) for a in aff]
            authors.append(Author(name=str(name), affiliations=affs))

        return authors

    def _detect_award(self, content: dict) -> str | None:
        for key in ("award", "awards", "presentation_type"):
            val = content.get(key, "")
            if isinstance(val, dict):
                val = val.get("value", "")
            if val and any(
                kw in str(val).lower()
                for kw in ("best", "award", "oral", "spotlight", "highlight")
            ):
                return str(val)
        return None
