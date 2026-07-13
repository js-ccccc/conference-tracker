"""论文去重与合并"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

from src.models import Author, Paper


class Deduplicator:
    """基于标题相似度与作者重叠的去重合并"""

    def __init__(self, title_threshold: float = 0.85):
        self.title_threshold = title_threshold

    def deduplicate(self, papers: list[Paper]) -> list[Paper]:
        if not papers:
            return []

        merged: list[Paper] = []
        for paper in papers:
            duplicate_idx = self._find_duplicate(paper, merged)
            if duplicate_idx is not None:
                merged[duplicate_idx] = self._merge_papers(merged[duplicate_idx], paper)
            else:
                merged.append(paper)
        return merged

    def _find_duplicate(self, paper: Paper, existing: list[Paper]) -> Optional[int]:
        if paper.paper_id:
            for i, ex in enumerate(existing):
                if ex.paper_id and paper.paper_id == ex.paper_id:
                    return i

        norm_title = self._normalize_title(paper.title)
        for i, ex in enumerate(existing):
            ex_norm = self._normalize_title(ex.title)
            if norm_title == ex_norm:
                return i
            if self._title_similarity(norm_title, ex_norm) >= self.title_threshold:
                return i
        return None

    @staticmethod
    def _normalize_title(title: str) -> str:
        title = unicodedata.normalize("NFKD", title)
        title = title.lower()
        title = re.sub(r"[^\w\s]", "", title)
        title = re.sub(r"\s+", " ", title).strip()
        return title

    @staticmethod
    def _title_similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        set_a = set(a.split())
        set_b = set(b.split())
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union

    def _merge_papers(self, base: Paper, other: Paper) -> Paper:
        if not base.abstract and other.abstract:
            base.abstract = other.abstract
        if not base.url and other.url:
            base.url = other.url
        if not base.award and other.award:
            base.award = other.award

        base.authors = self._merge_authors(base.authors, other.authors)

        sources = {base.source, other.source}
        base.source = "+".join(sorted(sources))

        base.has_tsinghua = base.has_tsinghua or other.has_tsinghua
        base.has_peking = base.has_peking or other.has_peking
        base.is_domestic = base.is_domestic or other.is_domestic

        return base

    def _merge_authors(
        self, authors_a: list[Author], authors_b: list[Author]
    ) -> list[Author]:
        merged = list(authors_a)
        existing_names = {a.name.lower() for a in authors_a}

        for author in authors_b:
            if author.name.lower() not in existing_names:
                merged.append(author)
                existing_names.add(author.name.lower())
            else:
                for existing in merged:
                    if existing.name.lower() == author.name.lower():
                        for aff in author.affiliations:
                            if aff not in existing.affiliations:
                                existing.affiliations.append(aff)
                        for tag in author.tags:
                            if tag not in existing.tags:
                                existing.tags.append(tag)
        return merged
