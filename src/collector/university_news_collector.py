"""高校官网新闻采集器"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.collector.base import BaseCollector
from src.models import Author, Conference, Paper

logger = logging.getLogger(__name__)


class UniversityNewsCollector(BaseCollector):
    """抓取清华、北大计算机学院官网的中稿喜报"""

    CONFERENCE_PATTERNS = [
        r"ACL\s*2026",
        r"ICML\s*2026",
        r"SIGGRAPH\s*2026",
        r"DAC\s*2026",
        r"KDD\s*2026",
        r"USENIX\s*Security\s*2026",
        r"IJCAI\s*2026",
        r"VLDB\s*2026",
        r"ISSTA\s*2026",
        r"ASE\s*2026",
        r"EMNLP\s*2026",
        r"FOCS\s*2026",
        r"NeurIPS\s*2026",
    ]

    def __init__(self, settings: dict[str, Any]):
        super().__init__(settings)
        self.news_config = settings.get("university_news", {})

    @property
    def source_name(self) -> str:
        return "university_news"

    def collect(self, conference: Conference, source_config: dict) -> list[Paper]:
        papers: list[Paper] = []
        pattern = re.compile(
            rf"{re.escape(conference.abbr)}\s*{conference.date_start[:4]}",
            re.IGNORECASE,
        )

        for uni_name, uni_cfg in self.news_config.items():
            if not uni_cfg:
                continue
            uni_papers = self._scrape_university(uni_name, uni_cfg, pattern, conference)
            papers.extend(uni_papers)

        logger.info(
            "University news: collected %d papers for %s",
            len(papers),
            conference.abbr,
        )
        return papers

    def _scrape_university(
        self,
        uni_name: str,
        uni_cfg: dict,
        pattern: re.Pattern,
        conference: Conference,
    ) -> list[Paper]:
        base_url = uni_cfg.get("url", "")
        search_path = uni_cfg.get("search_path", "/")
        page_url = urljoin(base_url, search_path)

        response = self.get(page_url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        papers: list[Paper] = []

        for link in soup.find_all("a", href=True):
            title_text = link.get_text(strip=True)
            if not title_text or not pattern.search(title_text):
                continue

            article_url = urljoin(base_url, link["href"])
            article_papers = self._parse_article(article_url, uni_name, conference)
            papers.extend(article_papers)

        return papers

    def _parse_article(
        self, url: str, uni_name: str, conference: Conference
    ) -> list[Paper]:
        response = self.get(url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        content = soup.get_text(separator="\n", strip=True)
        papers: list[Paper] = []

        title_patterns = [
            r"[《「]([^》」]+)[》」]",
            r"\"([^\"]{10,})\"",
            r"'([^']{10,})'",
        ]

        for pat in title_patterns:
            for match in re.finditer(pat, content):
                title = match.group(1).strip()
                if len(title) < 10:
                    continue
                affiliation = (
                    "清华大学" if uni_name == "tsinghua" else "北京大学"
                )
                papers.append(
                    Paper(
                        title=title,
                        authors=[Author(name="（见新闻）", affiliations=[affiliation])],
                        url=url,
                        source=self.source_name,
                        paper_id=f"{uni_name}:{hash(title)}",
                    )
                )

        return papers
