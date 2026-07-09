"""机构信息补全（OpenAlex / Crossref / ACL Anthology DOI）"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any
from urllib.parse import urlparse

import requests

from src.models import Author, Paper

logger = logging.getLogger(__name__)

ACL_DOI_PREFIX = "10.18653/v1/"


class AffiliationEnricher:
    """为缺少机构信息的论文补全作者机构"""

    def __init__(self, settings: dict[str, Any]):
        enrich_cfg = settings.get("enrichment", {})
        self.settings = enrich_cfg
        self.enabled = enrich_cfg.get("enabled", True)
        self.max_papers = enrich_cfg.get("max_papers_per_conference", 300)
        self.max_authors_per_paper = enrich_cfg.get("max_authors_per_paper", 6)
        self.request_delay = enrich_cfg.get("request_delay", 0.15)
        self.openalex_mailto = enrich_cfg.get(
            "openalex_mailto", "conference-tracker@example.com"
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": f"ConferenceTracker/1.0 (mailto:{self.openalex_mailto})",
                "Accept": "application/json",
            }
        )
        self._last_request = 0.0

    def enrich(self, papers: list[Paper]) -> list[Paper]:
        if not self.enabled or not papers:
            return papers

        enriched_count = 0
        limit = min(len(papers), self.max_papers)
        author_fallback_limit = min(
            limit, self.settings.get("max_author_fallback_papers", 40)
        )

        for i, paper in enumerate(papers[:limit]):
            if self._has_affiliations(paper):
                continue
            if self._enrich_from_openalex_work(paper):
                enriched_count += 1
                continue
            if self._enrich_from_crossref(paper):
                enriched_count += 1
                continue
            if i < author_fallback_limit and self._enrich_from_openalex_authors(paper):
                enriched_count += 1

        logger.info(
            "Affiliation enrichment: %d/%d papers updated",
            enriched_count,
            limit,
        )
        return papers

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self._last_request = time.time()

    def _get(self, url: str, params: dict | None = None) -> dict | None:
        for attempt in range(3):
            try:
                self._rate_limit()
                response = self.session.get(url, params=params, timeout=30)
                if response.status_code == 429:
                    time.sleep(2 ** (attempt + 1))
                    continue
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                logger.debug("Enrichment request failed: %s - %s", url, exc)
                if attempt < 2:
                    time.sleep(2**attempt)
        return None

    @staticmethod
    def _has_affiliations(paper: Paper) -> bool:
        return any(author.affiliations for author in paper.authors)

    @staticmethod
    def extract_doi(paper: Paper) -> str | None:
        candidates: list[str] = []
        if paper.url:
            candidates.append(paper.url)
        if paper.paper_id and paper.paper_id.startswith("10."):
            candidates.append(paper.paper_id)

        for raw in candidates:
            if "doi.org/" in raw:
                return raw.split("doi.org/", 1)[1].split("?", 1)[0]
            if raw.startswith("10."):
                return raw

        for raw in candidates:
            if "aclanthology.org/" in raw:
                path = urlparse(raw).path.strip("/")
                if path:
                    return f"{ACL_DOI_PREFIX}{path}"

        return None

    def _enrich_from_openalex_work(self, paper: Paper) -> bool:
        doi = self.extract_doi(paper)
        if not doi:
            return False

        data = self._get(f"https://api.openalex.org/works/https://doi.org/{doi}")
        if not data:
            return False

        return self._apply_openalex_authorships(paper, data.get("authorships", []))

    def _enrich_from_crossref(self, paper: Paper) -> bool:
        doi = self.extract_doi(paper)
        if not doi:
            return False

        data = self._get(f"https://api.crossref.org/works/{doi}")
        if not data:
            return False

        updated = False
        message = data.get("message", {})
        for i, author_data in enumerate(message.get("author", [])):
            affs = []
            for aff in author_data.get("affiliation", []):
                name = aff.get("name", "")
                if name:
                    affs.append(name)
            if affs and i < len(paper.authors):
                paper.authors[i].affiliations = affs
                updated = True
            elif affs:
                given = author_data.get("given", "")
                family = author_data.get("family", "")
                name = f"{given} {family}".strip()
                paper.authors.append(Author(name=name, affiliations=affs))
                updated = True
        return updated

    def _enrich_from_openalex_authors(self, paper: Paper) -> bool:
        updated = False
        for author in paper.authors[: self.max_authors_per_paper]:
            if author.affiliations:
                continue
            data = self._get(
                "https://api.openalex.org/authors",
                params={"search": author.name, "per_page": 1},
            )
            if not data or not data.get("results"):
                continue

            result = data["results"][0]
            insts = result.get("last_known_institutions") or []
            affs = [i.get("display_name", "") for i in insts if i.get("display_name")]
            if affs:
                author.affiliations = affs
                updated = True
        return updated

    def _apply_openalex_authorships(
        self, paper: Paper, authorships: list[dict]
    ) -> bool:
        if not authorships:
            return False

        updated = False
        if not paper.authors:
            for item in authorships:
                name = item.get("author", {}).get("display_name", "")
                affs = [
                    i.get("display_name", "")
                    for i in item.get("institutions", [])
                    if i.get("display_name")
                ]
                if name:
                    paper.authors.append(Author(name=name, affiliations=affs))
                    if affs:
                        updated = True
            return updated

        for i, author in enumerate(paper.authors):
            if i >= len(authorships):
                break
            if author.affiliations:
                continue
            affs = [
                inst.get("display_name", "")
                for inst in authorships[i].get("institutions", [])
                if inst.get("display_name")
            ]
            if affs:
                author.affiliations = affs
                updated = True
        return updated
