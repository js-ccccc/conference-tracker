"""数据模型定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Author:
    name: str
    affiliations: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    chinese_name: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "affiliations": self.affiliations,
            "tags": self.tags,
            "chinese_name": self.chinese_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Author:
        return cls(
            name=data.get("name", ""),
            affiliations=data.get("affiliations", []),
            tags=data.get("tags", []),
            chinese_name=data.get("chinese_name"),
        )


@dataclass
class Paper:
    title: str
    authors: list[Author] = field(default_factory=list)
    abstract: Optional[str] = None
    url: Optional[str] = None
    award: Optional[str] = None
    source: str = "unknown"
    paper_id: Optional[str] = None
    is_domestic: bool = False
    has_tsinghua: bool = False
    has_peking: bool = False

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "authors": [a.to_dict() for a in self.authors],
            "abstract": self.abstract,
            "url": self.url,
            "award": self.award,
            "source": self.source,
            "paper_id": self.paper_id,
            "is_domestic": self.is_domestic,
            "has_tsinghua": self.has_tsinghua,
            "has_peking": self.has_peking,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Paper:
        return cls(
            title=data.get("title", ""),
            authors=[Author.from_dict(a) for a in data.get("authors", [])],
            abstract=data.get("abstract"),
            url=data.get("url"),
            award=data.get("award"),
            source=data.get("source", "unknown"),
            paper_id=data.get("paper_id"),
            is_domestic=data.get("is_domestic", False),
            has_tsinghua=data.get("has_tsinghua", False),
            has_peking=data.get("has_peking", False),
        )


@dataclass
class Conference:
    id: str
    abbr: str
    full_name: str
    domain: str
    ccf_rating: str
    date_start: str
    date_end: str
    location_city: str
    location_country: str
    website: str
    submission_deadline: Optional[str] = None
    notification_date: Optional[str] = None
    papers: list[Paper] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return f"{self.full_name}（{self.abbr}）"

    @property
    def date_range(self) -> str:
        if self.date_start == self.date_end:
            return self._format_date(self.date_start)
        return f"{self._format_date(self.date_start)} - {self._format_date(self.date_end)}"

    @property
    def location(self) -> str:
        return f"{self.location_city}, {self.location_country}"

    @staticmethod
    def _format_date(iso_date: str) -> str:
        parts = iso_date.split("-")
        if len(parts) == 3:
            return f"{parts[0]}.{parts[1]}.{parts[2]}"
        return iso_date

    def domestic_papers(self) -> list[Paper]:
        return [p for p in self.papers if p.is_domestic]

    def tsinghua_papers(self) -> list[Paper]:
        return [p for p in self.papers if p.has_tsinghua]

    def peking_papers(self) -> list[Paper]:
        return [p for p in self.papers if p.has_peking]

    def highlighted_papers(self) -> list[Paper]:
        return [p for p in self.papers if p.has_tsinghua or p.has_peking]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "abbr": self.abbr,
            "full_name": self.full_name,
            "domain": self.domain,
            "ccf_rating": self.ccf_rating,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "location_city": self.location_city,
            "location_country": self.location_country,
            "website": self.website,
            "submission_deadline": self.submission_deadline,
            "notification_date": self.notification_date,
            "papers": [p.to_dict() for p in self.papers],
        }

    @classmethod
    def from_config(cls, config: dict) -> Conference:
        loc = config.get("location", {})
        return cls(
            id=config["id"],
            abbr=config["abbr"],
            full_name=config["full_name"],
            domain=config["domain"],
            ccf_rating=config["ccf_rating"],
            date_start=config["date_start"],
            date_end=config["date_end"],
            location_city=loc.get("city", ""),
            location_country=loc.get("country", ""),
            website=config.get("website", ""),
            submission_deadline=config.get("submission_deadline"),
            notification_date=config.get("notification_date"),
        )

    @classmethod
    def from_dict(cls, data: dict) -> Conference:
        conf = cls(
            id=data["id"],
            abbr=data["abbr"],
            full_name=data["full_name"],
            domain=data["domain"],
            ccf_rating=data["ccf_rating"],
            date_start=data["date_start"],
            date_end=data["date_end"],
            location_city=data["location_city"],
            location_country=data["location_country"],
            website=data["website"],
            submission_deadline=data.get("submission_deadline"),
            notification_date=data.get("notification_date"),
        )
        conf.papers = [Paper.from_dict(p) for p in data.get("papers", [])]
        return conf
