"""微信公众号文章采集器"""

from __future__ import annotations

import logging
import re
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


class WeChatCollector(BaseCollector):
    """通过搜狗微信搜索及配置的公众号文章页抓取中稿信息"""

    SOGOU_SEARCH = "https://weixin.sogou.com/weixin?type=2&query={query}"

    def __init__(self, settings: dict[str, Any]):
        super().__init__(settings)
        wechat_cfg = settings.get("wechat", {})
        self.accounts = wechat_cfg.get("accounts", [])
        self.max_articles = wechat_cfg.get("max_articles_per_query", 8)
        self.use_sogou = wechat_cfg.get("use_sogou_search", True)
        self.session.headers.update(
            {
                "Referer": "https://weixin.sogou.com/",
                "Accept": "text/html,application/xhtml+xml",
            }
        )

    @property
    def source_name(self) -> str:
        return "wechat"

    def collect(self, conference: Conference, source_config: dict) -> list[Paper]:
        papers: list[Paper] = []

        if self.use_sogou:
            papers.extend(self._search_sogou(conference))

        for account in self.accounts:
            if not account.get("enabled", True):
                continue
            papers.extend(self._scrape_account(account, conference))

        logger.info(
            "WeChat: collected %d papers for %s", len(papers), conference.abbr
        )
        return papers

    def _search_sogou(self, conference: Conference) -> list[Paper]:
        queries = [
            f"{conference.abbr} {conference.date_start[:4]} 清华",
            f"{conference.abbr} {conference.date_start[:4]} 北大",
            f"{conference.abbr} {conference.date_start[:4]} 中稿",
            f"{conference.abbr} {conference.date_start[:4]} 录用",
        ]
        papers: list[Paper] = []
        seen_urls: set[str] = set()

        for query in queries:
            url = self.SOGOU_SEARCH.format(query=quote(query))
            response = self.get(url)
            if not response:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            for item in soup.select("div.txt-box, li, .news-box")[: self.max_articles]:
                link = item.find("a", href=True)
                if not link:
                    continue
                title = link.get_text(strip=True)
                if not text_mentions_conference(title, conference):
                    if not conference_pattern(conference).search(title):
                        continue
                article_url = link["href"]
                if article_url in seen_urls:
                    continue
                seen_urls.add(article_url)
                papers.extend(self._fetch_wechat_article(article_url, conference))

        return papers

    def _scrape_account(self, account: dict, conference: Conference) -> list[Paper]:
        pages = account.get("article_pages", [])
        papers: list[Paper] = []
        pattern = conference_pattern(conference)
        affiliation = account.get("affiliation")

        for page_url in pages:
            response = self.get(page_url)
            if not response:
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            for link in soup.find_all("a", href=True):
                title = link.get_text(strip=True)
                if not pattern.search(title):
                    continue
                article_url = urljoin(page_url, link["href"])
                article_papers = self._fetch_wechat_article(
                    article_url, conference, default_affiliation=affiliation
                )
                papers.extend(article_papers)

        return papers

    def _fetch_wechat_article(
        self,
        url: str,
        conference: Conference,
        default_affiliation: str | None = None,
    ) -> list[Paper]:
        if url.startswith("/link?"):
            url = urljoin("https://weixin.sogou.com", url)

        response = self.get(url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # 微信公众号正文常见结构
        content_elem = (
            soup.select_one("#js_content")
            or soup.select_one(".rich_media_content")
            or soup.select_one("article")
        )
        content = (
            content_elem.get_text(separator="\n", strip=True)
            if content_elem
            else soup.get_text(separator="\n", strip=True)
        )

        if not text_mentions_conference(content, conference):
            return []

        return papers_from_article(
            content,
            conference,
            self.source_name,
            url,
            default_affiliation=default_affiliation,
        )
