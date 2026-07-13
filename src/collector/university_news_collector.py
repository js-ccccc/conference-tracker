"""高校官网新闻采集器"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.collector.base import BaseCollector
from src.collector.news_parser import conference_pattern, papers_from_article
from src.models import Conference, Paper

logger = logging.getLogger(__name__)


class UniversityNewsCollector(BaseCollector):
    """抓取各高校官网/院系网站的中稿喜报"""

    def __init__(self, settings: dict[str, Any]):
        super().__init__(settings)
        self.universities = settings.get("university_news", {}).get("sites", [])

    @property
    def source_name(self) -> str:
        return "university_news"

    def collect(self, conference: Conference, source_config: dict) -> list[Paper]:
        papers: list[Paper] = []
        pattern = conference_pattern(conference)

        for uni in self.universities:
            if not uni.get("enabled", True):
                continue
            papers.extend(self._scrape_university(uni, pattern, conference))

        logger.info(
            "University news: collected %d papers for %s",
            len(papers),
            conference.abbr,
        )
        return papers

    def _scrape_university(
        self, uni: dict, pattern, conference: Conference
    ) -> list[Paper]:
        base_url = uni.get("url", "")
        affiliation = uni.get("affiliation", uni.get("name", ""))
        papers: list[Paper] = []

        paths = uni.get("news_paths", [uni.get("search_path", "/")])
        max_articles = uni.get("max_articles", 15)

        for search_path in paths:
            page_url = urljoin(base_url, search_path)
            response = self.get(page_url)
            if not response:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            article_count = 0

            for link in soup.find_all("a", href=True):
                title_text = link.get_text(strip=True)
                if not title_text or not pattern.search(title_text):
                    continue

                article_url = urljoin(base_url, link["href"])
                papers.extend(
                    self._parse_article(article_url, conference, affiliation)
                )
                article_count += 1
                if article_count >= max_articles:
                    break

        return papers

    def _parse_article(
        self, url: str, conference: Conference, affiliation: str
    ) -> list[Paper]:
        response = self.get(url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        content = soup.get_text(separator="\n", strip=True)
        return papers_from_article(
            content,
            conference,
            self.source_name,
            url,
            default_affiliation=affiliation,
        )
