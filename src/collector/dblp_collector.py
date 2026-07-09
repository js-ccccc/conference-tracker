"""DBLP API 采集器"""

from __future__ import annotations

import logging
import re
from typing import Any
from xml.etree import ElementTree

from src.collector.base import BaseCollector
from src.models import Author, Conference, Paper

logger = logging.getLogger(__name__)

PROCEEDINGS_TITLE_MARKERS = (
    "proceedings of",
    "conference on",
    "international conference",
    "symposium on",
    "workshop on",
)


class DBLPCollector(BaseCollector):
    """通过 DBLP API 按会议检索论文"""

    def __init__(self, settings: dict[str, Any]):
        super().__init__(settings)
        self.api_base = settings.get("dblp", {}).get(
            "api_base", "https://dblp.org/search/publ/api"
        )
        self.max_papers = settings.get("collector", {}).get("dblp_max_papers", 500)

    @property
    def source_name(self) -> str:
        return "dblp"

    def collect(self, conference: Conference, source_config: dict) -> list[Paper]:
        if not source_config or not source_config.get("key"):
            logger.info("No DBLP key for %s, skipping", conference.abbr)
            return []

        dblp_key = source_config["key"]
        papers: list[Paper] = []

        # 优先用 proceedings key 查询（如 conf/acl/2026），比 venue: 语法更准确
        papers = self._search_by_query(dblp_key)

        if not papers:
            query = f"venue:{conference.abbr}:{conference.date_start[:4]}"
            papers = self._search_by_query(query)

        if not papers:
            papers = self._search_by_key(dblp_key)

        papers = self._filter_proceedings(papers)[: self.max_papers]
        logger.info("DBLP: collected %d papers for %s", len(papers), conference.abbr)
        return papers

    def _search_by_query(self, query: str) -> list[Paper]:
        papers: list[Paper] = []
        first = 0
        batch_size = 100

        while len(papers) < self.max_papers:
            batch = self._search(query, first, batch_size)
            if not batch:
                break
            papers.extend(batch)
            if len(batch) < batch_size:
                break
            first += batch_size

        return papers

    def _search(self, query: str, first: int, count: int) -> list[Paper]:
        params = {"q": query, "format": "json", "h": count, "f": first}
        response = self.get(self.api_base, params=params)
        if not response or response.status_code != 200:
            if response and response.status_code == 429:
                logger.warning("DBLP rate limited, stopping pagination")
            return []

        try:
            data = response.json()
        except ValueError:
            return []

        hits = data.get("result", {}).get("hits", {}).get("hit", [])
        if isinstance(hits, dict):
            hits = [hits]

        papers = []
        for hit in hits:
            paper = self._parse_hit(hit)
            if paper:
                papers.append(paper)
        return papers

    def _search_by_key(self, dblp_key: str) -> list[Paper]:
        url = f"https://dblp.org/rec/{dblp_key}.xml"
        response = self.get(url)
        if not response:
            return []

        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError:
            return []

        papers: list[Paper] = []
        for pub in root.iter():
            if pub.tag in ("inproceedings", "article"):
                paper = self._parse_xml_pub(pub)
                if paper:
                    papers.append(paper)
        return papers

    def _filter_proceedings(self, papers: list[Paper]) -> list[Paper]:
        filtered = []
        for paper in papers:
            title_lower = paper.title.lower().strip()
            if title_lower.startswith("proceedings of the"):
                continue
            if title_lower.startswith("proceedings of "):
                continue
            if "proceedings" in title_lower and len(paper.authors) >= 5:
                continue
            filtered.append(paper)
        return filtered

    def _parse_hit(self, hit: dict) -> Paper | None:
        info = hit.get("info", {})
        title = info.get("title", "")
        if not title:
            return None

        title = re.sub(r"</?[^>]+>", "", title).strip()
        authors = self._parse_authors_json(info.get("authors", {}))
        url = self._extract_url(info)
        paper_id = info.get("key", "")

        return Paper(
            title=title,
            authors=authors,
            url=url,
            source=self.source_name,
            paper_id=paper_id,
        )

    @staticmethod
    def _extract_url(info: dict) -> str | None:
        ee = info.get("ee")
        if isinstance(ee, str):
            return ee
        if isinstance(ee, list) and ee:
            return str(ee[0])
        return info.get("url")

    def _parse_authors_json(self, authors_data: dict | list) -> list[Author]:
        if isinstance(authors_data, dict):
            author_list = authors_data.get("author", [])
        else:
            author_list = authors_data

        if isinstance(author_list, dict):
            author_list = [author_list]

        if isinstance(author_list, str):
            author_list = [author_list]

        authors: list[Author] = []
        for item in author_list:
            if isinstance(item, dict):
                authors.append(Author(name=str(item.get("text", ""))))
            else:
                authors.append(Author(name=str(item)))
        return authors

    def _parse_xml_pub(self, elem) -> Paper | None:
        title_elem = elem.find("title")
        if title_elem is None or not title_elem.text:
            return None

        title = title_elem.text.strip()
        authors = []
        for author_elem in elem.findall("author"):
            if author_elem.text:
                affs = []
                if author_elem.get("affiliation"):
                    affs = [author_elem.get("affiliation")]
                authors.append(Author(name=author_elem.text, affiliations=affs))

        url = None
        for ee in elem.findall("ee"):
            if ee.text:
                url = ee.text
                break

        return Paper(
            title=title,
            authors=authors,
            url=url,
            source=self.source_name,
            paper_id=elem.findtext("key"),
        )
