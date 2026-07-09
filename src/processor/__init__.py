"""数据处理流水线"""

from __future__ import annotations

import logging
from typing import Any

from src.models import Conference, Paper
from src.processor.affiliation_enricher import AffiliationEnricher
from src.processor.deduplicator import Deduplicator
from src.processor.institution_matcher import InstitutionMatcher

logger = logging.getLogger(__name__)


class DataProcessor:
    """机构归一化、清北标注、去重合并"""

    def __init__(self, institutions_config: dict[str, Any], settings: dict[str, Any] | None = None):
        self.matcher = InstitutionMatcher(institutions_config)
        self.deduplicator = Deduplicator()
        self.settings = settings or {}
        self.enricher = AffiliationEnricher(self.settings)

    def process_papers(self, papers: list[Paper], enrich: bool = True) -> list[Paper]:
        if enrich and self.enricher.enabled:
            papers = self.enricher.enrich(papers)
        tagged = [self.matcher.process_paper(p) for p in papers]
        deduped = self.deduplicator.deduplicate(tagged)
        domestic = [p for p in deduped if p.is_domestic]
        logger.info(
            "Processed %d papers -> %d after dedup -> %d domestic (keeping all %d)",
            len(papers),
            len(deduped),
            len(domestic),
            len(deduped),
        )
        return deduped

    def process_conference(
        self, conference: Conference, papers: list[Paper], enrich: bool = True
    ) -> Conference:
        conference.papers = self.process_papers(papers, enrich=enrich)
        return conference

    @property
    def institution_matcher(self) -> InstitutionMatcher:
        return self.matcher
