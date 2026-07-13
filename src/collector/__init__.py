"""数据采集器统一入口"""

from __future__ import annotations

import logging
from typing import Any

from src.collector.base import BaseCollector
from src.collector.conference_official_collector import ConferenceOfficialCollector
from src.collector.tech_news_collector import TechNewsCollector
from src.collector.university_news_collector import UniversityNewsCollector
from src.collector.wechat_collector import WeChatCollector
from src.models import Conference, Paper

logger = logging.getLogger(__name__)


class CollectorManager:
    """管理多数据源采集：会议官网、科技新闻、学校官网、微信公众号"""

    GLOBAL_SOURCES = ("tech_news", "university_news", "wechat")

    def __init__(self, settings: dict[str, Any]):
        self.collectors: dict[str, BaseCollector] = {
            "official": ConferenceOfficialCollector(settings),
            "tech_news": TechNewsCollector(settings),
            "university_news": UniversityNewsCollector(settings),
            "wechat": WeChatCollector(settings),
        }

    def collect_all(self, conference: Conference, conf_config: dict) -> list[Paper]:
        all_papers: list[Paper] = []
        sources = conf_config.get("sources", {})

        for source_name, collector in self.collectors.items():
            if source_name in self.GLOBAL_SOURCES:
                source_config = {}
            else:
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
