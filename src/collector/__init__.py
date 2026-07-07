"""数据采集器统一入口"""

from __future__ import annotations

import logging
from typing import Any

from src.collector.base import BaseCollector
from src.collector.dblp_collector import DBLPCollector
from src.collector.openreview_collector import OpenReviewCollector
from src.collector.university_news_collector import UniversityNewsCollector
from src.models import Conference, Paper

logger = logging.getLogger(__name__)


class CollectorManager:
    """管理多数据源采集，单源失败不影响整体"""

    def __init__(self, settings: dict[str, Any]):
        self.collectors: dict[str, BaseCollector] = {
            "openreview": OpenReviewCollector(settings),
            "dblp": DBLPCollector(settings),
            "university_news": UniversityNewsCollector(settings),
        }

    def collect_all(self, conference: Conference, conf_config: dict) -> list[Paper]:
        all_papers: list[Paper] = []
        sources = conf_config.get("sources", {})

        for source_name, collector in self.collectors.items():
            source_config = sources.get(source_name)
            if source_config is None and source_name != "university_news":
                continue

            try:
                if source_name == "university_news":
                    papers = collector.collect(conference, {})
                else:
                    papers = collector.collect(conference, source_config or {})
                all_papers.extend(papers)
                logger.info(
                    "%s: %d papers from %s",
                    conference.abbr,
                    len(papers),
                    source_name,
                )
            except Exception as exc:
                logger.error(
                    "Collector %s failed for %s: %s",
                    source_name,
                    conference.abbr,
                    exc,
                    exc_info=True,
                )

        return all_papers
