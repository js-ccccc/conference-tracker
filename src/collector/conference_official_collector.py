"""会议官网采集器"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.collector.base import BaseCollector
from src.collector.news_parser import text_mentions_conference
from src.models import Author, Conference, Paper

logger = logging.getLogger(__name__)


class ConferenceOfficialCollector(BaseCollector):
    """从各会议官网抓取录用论文、Program 页面信息"""

    def __init__(self, settings: dict[str, Any]):
        super().__init__(settings)
        self.settings = settings

    @property
    def source_name(self) -> str:
        return "conference_official"

    def collect(self, conference: Conference, source_config: dict) -> list[Paper]:
        if not source_config:
            source_config = {}

        pages: list[str] = list(source_config.get("pages", []))
        if conference.website and conference.website not in pages:
            pages.insert(0, conference.website)

        papers: list[Paper] = []
        seen_ids: set[str] = set()

        for page_url in pages:
            for paper in self._scrape_page(page_url, conference):
                key = paper.paper_id or paper.title
                if key in seen_ids:
                    continue
                seen_ids.add(key)
                papers.append(paper)

        max_papers = source_config.get(
            "max_papers",
            self.settings.get("collector", {}).get("official_max_papers", 800),
        )
        papers = papers[:max_papers]

        logger.info(
            "Conference official: collected %d papers for %s",
            len(papers),
            conference.abbr,
        )
        return papers

    def _scrape_page(self, page_url: str, conference: Conference) -> list[Paper]:
        response = self.get(page_url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        papers: list[Paper] = []

        # ACL Anthology / OpenReview 论文链接
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if ".pdf" in href.lower() or href.lower().endswith((".bib", ".abs")):
                continue

            paper_url = urljoin(page_url, href)
            is_acl_paper = bool(
                re.search(r"/20\d{2}\.[a-z0-9.-]+\.\d+/?$", href)
                or re.search(r"aclanthology\.org/20\d{2}\.", href)
            )

            if is_acl_paper or "openreview.net/forum" in href:
                title = self._extract_title_from_link(link)
                if len(title) < 12:
                    continue
                if title.lower().startswith("proceedings of"):
                    continue
                papers.append(
                    Paper(
                        title=title,
                        authors=[],
                        url=paper_url,
                        source=self.source_name,
                        paper_id=href,
                    )
                )

        # 页面标题列表（常见 program 页结构）
        for selector in (
            "li.paper",
            "div.paper",
            "tr.odd",
            "tr.even",
            ".accepted-paper",
            ".paper-title",
        ):
            for elem in soup.select(selector):
                title_elem = elem.find(["a", "span", "strong"]) or elem
                title = title_elem.get_text(strip=True)
                if len(title) < 12:
                    continue
                link = elem.find("a", href=True)
                url = urljoin(page_url, link["href"]) if link else page_url
                papers.append(
                    Paper(
                        title=title,
                        authors=[],
                        url=url,
                        source=self.source_name,
                        paper_id=f"official:{hash(title)}",
                    )
                )

        # 新闻/公告类页面（非论文列表页）
        page_text = soup.get_text(separator="\n", strip=True)
        if not papers and text_mentions_conference(page_text, conference):
            from src.collector.news_parser import papers_from_article

            papers.extend(
                papers_from_article(
                    page_text, conference, self.source_name, page_url
                )
            )

        return papers

    @staticmethod
    def _extract_title_from_link(link) -> str:
        title = link.get_text(strip=True)
        if title and title.lower() not in ("pdf", "bib", "abs"):
            return title

        for attr in ("title", "aria-label"):
            if link.get(attr):
                return str(link[attr]).strip()

        parent = link.find_parent(["p", "li", "div", "span"])
        if parent:
            text = parent.get_text(separator=" ", strip=True)
            text = re.sub(r"\s*(pdf|bib|abs)\s*$", "", text, flags=re.I)
            if len(text) >= 12:
                return text[:300]

        return ""
