"""arXiv API 采集器"""

from __future__ import annotations

import logging
import re
from typing import Any
from xml.etree import ElementTree

from src.collector.base import BaseCollector
from src.models import Author, Conference, Paper

logger = logging.getLogger(__name__)

ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivCollector(BaseCollector):
    """通过 arXiv API 检索与各会议对应的预印本论文"""

    def __init__(self, settings: dict[str, Any]):
        super().__init__(settings)
        arxiv_cfg = settings.get("arxiv", {})
        self.api_base = arxiv_cfg.get(
            "api_base", "http://export.arxiv.org/api/query"
        )
        self.max_results = arxiv_cfg.get("max_results_per_conference", 50)
        self.page_size = arxiv_cfg.get("page_size", 50)
        # arXiv 要求请求间隔 >= 3 秒
        self.request_delay = max(self.request_delay, 3.0)

    @property
    def source_name(self) -> str:
        return "arxiv"

    def collect(self, conference: Conference, source_config: dict) -> list[Paper]:
        if not source_config:
            source_config = {}

        categories = source_config.get("categories", [])
        keywords = source_config.get("keywords", [])
        year = conference.date_start[:4]

        if not keywords:
            keywords = self._default_keywords(conference, year)

        papers: list[Paper] = []
        seen_ids: set[str] = set()

        # 策略1：按 arXiv 分类检索最新论文（不限制关键词，获取该领域最新预印本）
        if categories:
            cat_query = " OR ".join(f"cat:{c}" for c in categories)
            logger.info("arXiv: searching by category '%s' for %s", cat_query, conference.abbr)
            for batch in self._query_arxiv(cat_query):
                for paper in batch:
                    if self._add_paper(paper, seen_ids, papers):
                        return papers

        # 策略2：按关键词检索（匹配论文标题/摘要中提到会议名的）
        for kw in keywords[:2]:
            logger.info("arXiv: searching keyword '%s' for %s", kw, conference.abbr)
            for batch in self._query_arxiv(kw):
                for paper in batch:
                    if self._add_paper(paper, seen_ids, papers):
                        return papers

        logger.info("arXiv: collected %d papers for %s", len(papers), conference.abbr)
        return papers

    def _add_paper(
        self, paper: Paper, seen_ids: set[str], papers: list[Paper]
    ) -> bool:
        """添加论文到列表，返回是否达到上限"""
        pid = paper.paper_id or paper.title
        if pid in seen_ids:
            return False
        seen_ids.add(pid)
        papers.append(paper)
        return len(papers) >= self.max_results

    @staticmethod
    def _default_keywords(conference: Conference, year: str) -> list[str]:
        return [f"{conference.abbr} {year}", conference.full_name]

    def _query_arxiv(self, query: str) -> list[list[Paper]]:
        start = 0
        while start < self.max_results:
            params = {
                "search_query": query,
                "start": start,
                "max_results": min(self.page_size, self.max_results - start),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            response = self.get(self.api_base, params=params)
            if not response:
                break

            batch = self._parse_response(response.text)
            if not batch:
                break

            yield batch
            start += len(batch)
            if len(batch) < self.page_size:
                break

    def _parse_response(self, xml_text: str) -> list[Paper]:
        papers: list[Paper] = []
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as exc:
            logger.warning("arXiv XML parse error: %s", exc)
            return papers

        for entry in root.findall("atom:entry", ARXIV_NS):
            paper = self._parse_entry(entry)
            if paper:
                papers.append(paper)
        return papers

    def _parse_entry(self, entry) -> Paper | None:
        title_elem = entry.find("atom:title", ARXIV_NS)
        if title_elem is None or not title_elem.text:
            return None

        title = re.sub(r"\s+", " ", title_elem.text).strip()

        arxiv_id = ""
        id_elem = entry.find("atom:id", ARXIV_NS)
        if id_elem is not None and id_elem.text:
            arxiv_id = id_elem.text.strip().rsplit("/", 1)[-1]

        authors: list[Author] = []
        for author_elem in entry.findall("atom:author", ARXIV_NS):
            name_elem = author_elem.find("atom:name", ARXIV_NS)
            if name_elem is not None and name_elem.text:
                authors.append(Author(name=name_elem.text.strip()))

        abstract_elem = entry.find("atom:summary", ARXIV_NS)
        abstract = abstract_elem.text.strip() if abstract_elem is not None else None

        published = ""
        pub_elem = entry.find("atom:published", ARXIV_NS)
        if pub_elem is not None and pub_elem.text:
            published = pub_elem.text.strip()[:10]

        categories: list[str] = []
        for cat in entry.findall("atom:category", ARXIV_NS):
            term = cat.get("term")
            if term:
                categories.append(term)

        url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None
        abstract_with_meta = abstract
        if published or categories:
            meta = []
            if published:
                meta.append(f"提交时间: {published}")
            if categories:
                meta.append(f"分类: {', '.join(categories)}")
            abstract_with_meta = (
                f"{abstract}\n\n[{'; '.join(meta)}]" if abstract else "; ".join(meta)
            )

        return Paper(
            title=title,
            authors=authors,
            abstract=abstract_with_meta,
            url=url,
            source=self.source_name,
            paper_id=arxiv_id,
        )
