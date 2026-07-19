"""数据采集器统一入口"""

from __future__ import annotations

import logging
from typing import Any

from src.collector.arxiv_collector import ArxivCollector
from src.collector.base import BaseCollector
from src.models import Conference, Paper

logger = logging.getLogger(__name__)


class CollectorManager:
    """以 arXiv 为主数据源的采集管理器"""

    def __init__(self, settings: dict[str, Any]):
        self.collectors: dict[str, BaseCollector] = {
            "arxiv": ArxivCollector(settings),
        }

    def collect_all(self, conference: Conference, conf_config: dict) -> list[Paper]:
        all_papers: list[Paper] = []
        sources = conf_config.get("sources", {})

        for source_name, collector in self.collectors.items():
            source_config = sources.get(source_name)
            if source_config is None:
                continue

            try:
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
