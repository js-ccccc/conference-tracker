"""机构名称归一化与清北识别"""

from __future__ import annotations

import re
from typing import Any

from src.models import Author, Paper


class InstitutionMatcher:
    """机构名称归一化、国内识别、清北标注"""

    def __init__(self, institutions_config: dict[str, Any]):
        self.highlight = institutions_config.get("highlight_institutions", {})
        self.domestic_keywords = institutions_config.get("domestic_keywords", [])
        self.aliases = institutions_config.get("aliases", {})

        self._tsinghua_patterns = self._compile_patterns(
            self.highlight.get("tsinghua", {}).get("keywords", [])
        )
        self._peking_patterns = self._compile_patterns(
            self.highlight.get("peking", {}).get("keywords", [])
        )
        self._domestic_patterns = self._compile_patterns(self.domestic_keywords)

        self.tsinghua_label = self.highlight.get("tsinghua", {}).get("label", "🔵清华")
        self.peking_label = self.highlight.get("peking", {}).get("label", "🔴北大")

    @staticmethod
    def _compile_patterns(keywords: list[str]) -> list[re.Pattern]:
        patterns = []
        for kw in keywords:
            escaped = re.escape(kw)
            patterns.append(re.compile(escaped, re.IGNORECASE))
        return patterns

    def normalize(self, affiliation: str) -> str:
        aff = affiliation.strip()
        for alias, canonical in self.aliases.items():
            if alias.lower() in aff.lower():
                return canonical
        return aff

    def _matches_any(self, text: str, patterns: list[re.Pattern]) -> bool:
        return any(p.search(text) for p in patterns)

    def is_tsinghua(self, affiliation: str) -> bool:
        return self._matches_any(affiliation, self._tsinghua_patterns)

    def is_peking(self, affiliation: str) -> bool:
        return self._matches_any(affiliation, self._peking_patterns)

    def is_domestic(self, affiliation: str) -> bool:
        normalized = self.normalize(affiliation)
        return self._matches_any(normalized, self._domestic_patterns)

    def tag_author(self, author: Author) -> Author:
        tags: list[str] = []
        normalized_affs = [self.normalize(a) for a in author.affiliations]

        for aff in author.affiliations + normalized_affs:
            if self.is_tsinghua(aff):
                if self.tsinghua_label not in tags:
                    tags.append(self.tsinghua_label)
            if self.is_peking(aff):
                if self.peking_label not in tags:
                    tags.append(self.peking_label)

        author.affiliations = normalized_affs if normalized_affs else author.affiliations
        author.tags = tags
        return author

    def process_paper(self, paper: Paper) -> Paper:
        has_tsinghua = False
        has_peking = False
        is_domestic = False

        for author in paper.authors:
            self.tag_author(author)
            if self.tsinghua_label in author.tags:
                has_tsinghua = True
            if self.peking_label in author.tags:
                has_peking = True
            for aff in author.affiliations:
                if self.is_domestic(aff):
                    is_domestic = True

        paper.has_tsinghua = has_tsinghua
        paper.has_peking = has_peking
        paper.is_domestic = is_domestic
        return paper

    def format_author_display(self, author: Author) -> str:
        tag_str = "".join(author.tags)
        return f"{author.name}{tag_str}"
