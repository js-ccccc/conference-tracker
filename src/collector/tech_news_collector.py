"""科技新闻网站采集器"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from src.collector.base import BaseCollector
from src.collector.news_parser import (
    conference_pattern,
    papers_from_article,
    text_mentions_conference,
)
from src.models import Conference, Paper

logger = logging.getLogger(__name__)


class TechNewsCollector(BaseCollector):
    """从机器之心、量子位等科技媒体抓取中稿报道"""

    def __init__(self, settings: dict[str, Any]):
        super().__init__(settings)
        self.sites = settings.get("tech_news", {}).get("sites", [])

    @property
    def source_name(self) -> str:
        return "tech_news"

    def collect(self, conference: Conference, source_config: dict) -> list[Paper]:
        papers: list[Paper] = []
        pattern = conference_pattern(conference)

        for site in self.sites:
            if not site.get("enabled", True):
                continue
            site_papers = self._scrape_site(site, pattern, conference)
            papers.extend(site_papers)

        logger.info(
            "Tech news: collected %d papers for %s", len(papers), conference.abbr
        )
        return papers

    def _scrape_site(
        self, site: dict, pattern, conference: Conference
    ) -> list[Paper]:
        base_url = site.get("url", "")
        list_path = site.get("list_path", "/")
        page_url = urljoin(base_url, list_path)

        response = self.get(page_url)
        if not response:
            return self._search_site(site, conference)

        soup = BeautifulSoup(response.text, "html.parser")
        papers: list[Paper] = []
        article_links: list[str] = []

        for link in soup.find_all("a", href=True):
            title = link.get_text(strip=True)
            if not title or not pattern.search(title):
                continue
            article_links.append(urljoin(base_url, link["href"]))

        for url in article_links[: site.get("max_articles", 10)]:
            papers.extend(self._parse_article(url, conference))

        if not papers:
            papers.extend(self._search_site(site, conference))

        return papers

    def _search_site(self, site: dict, conference: Conference) -> list[Paper]:
        search_tpl = site.get("search_url")
        if not search_tpl:
            return []

        query = f"{conference.abbr} {conference.date_start[:4]}"
        search_url = search_tpl.format(query=quote(query))
        response = self.get(search_url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        papers: list[Paper] = []
        base_url = site.get("url", "")

        for link in soup.find_all("a", href=True)[: site.get("max_articles", 8)]:
            title = link.get_text(strip=True)
            if not text_mentions_conference(title, conference):
                continue
            papers.extend(self._parse_article(urljoin(base_url, link["href"]), conference))

        return papers

    def _parse_article(self, url: str, conference: Conference) -> list[Paper]:
        response = self.get(url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        content = soup.get_text(separator="\n", strip=True)
        return papers_from_article(content, conference, self.source_name, url)
