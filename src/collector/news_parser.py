"""新闻/网页正文解析工具"""

from __future__ import annotations

import re

from src.models import Author, Conference, Paper

# 从中文报道中提取论文标题
TITLE_PATTERNS = [
    re.compile(r"[《「]([^》」]{8,})[》」]"),
    re.compile(r"\"([^\"]{12,})\""),
    re.compile(r"'([^']{12,})'"),
    re.compile(r"论文[《「]?([^》」\n]{10,80})[》」]?"),
    re.compile(r"题为[《「]([^》」]{8,})[》」]"),
]

# 从报道中提取作者（带机构时一并解析）
AUTHOR_LINE_PATTERN = re.compile(
    r"([^\s，,、]{2,8})\s*(?:教授|副教授|研究员|博士生|硕士生|学生)?"
    r"(?:来自|供职于|隶属于)?\s*([^，,\n]{2,30})"
)

INSTITUTION_HINTS = re.compile(
    r"(清华大学|北京大学|复旦大学|上海交通大学|浙江大学|南京大学|"
    r"中国科学技术大学|哈尔滨工业大学|中国科学院|香港大学|香港中文大学|"
    r"Tsinghua|Peking|Fudan|Zhejiang|Nanjing)"
)


def conference_pattern(conference: Conference) -> re.Pattern:
    year = conference.date_start[:4]
    abbr = re.escape(conference.abbr)
    return re.compile(rf"{abbr}\s*{year}|{year}\s*{abbr}", re.IGNORECASE)


def text_mentions_conference(text: str, conference: Conference) -> bool:
    return bool(conference_pattern(conference).search(text))


def extract_paper_titles(text: str) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()

    for pattern in TITLE_PATTERNS:
        for match in pattern.finditer(text):
            title = match.group(1).strip()
            title = re.sub(r"\s+", " ", title)
            if len(title) < 10 or len(title) > 200:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            titles.append(title)

    return titles


def extract_authors_with_affiliations(text: str) -> list[Author]:
    authors: list[Author] = []
    for match in AUTHOR_LINE_PATTERN.finditer(text):
        name, aff = match.group(1).strip(), match.group(2).strip()
        if name and aff and INSTITUTION_HINTS.search(aff):
            authors.append(Author(name=name, affiliations=[aff]))
    return authors


def papers_from_article(
    text: str,
    conference: Conference,
    source: str,
    url: str,
    default_affiliation: str | None = None,
) -> list[Paper]:
    if not text_mentions_conference(text, conference):
        return []

    if not _looks_like_acceptance_news(text):
        return []

    papers: list[Paper] = []
    authors = extract_authors_with_affiliations(text)
    titles = extract_paper_titles(text)

    if not titles:
        return papers

    for title in titles:
        paper_authors = [a for a in authors if _valid_author_name(a.name)]
        if not paper_authors and default_affiliation:
            paper_authors = [
                Author(name="（见报道）", affiliations=[default_affiliation])
            ]
        papers.append(
            Paper(
                title=title,
                authors=paper_authors,
                url=url,
                source=source,
                paper_id=f"{source}:{hash(title)}",
            )
        )

    return papers


def _looks_like_acceptance_news(text: str) -> bool:
    keywords = ("中稿", "录用", "入选", "喜报", "祝贺", "篇论文", "接收", "被接收", "恭喜")
    return any(kw in text for kw in keywords)


def _valid_author_name(name: str) -> bool:
    if not name or len(name) < 2:
        return False
    if name.startswith("http") or name.isascii() and len(name) < 3:
        return False
    return True
