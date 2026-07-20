"""Markdown 报告生成器"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config_loader import get_project_root
from src.models import Conference, Paper
from src.processor.institution_matcher import InstitutionMatcher

logger = logging.getLogger(__name__)


class ReportGenerator:
    """使用 Jinja2 模板生成结构化 Markdown 报告"""

    def __init__(
        self,
        matcher: InstitutionMatcher,
        output_dir: str | Path = "reports",
        template_name: str = "report.md.j2",
    ):
        self.matcher = matcher
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        template_dir = get_project_root() / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(disabled_extensions=("j2", "md")),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = self.env.get_template(template_name)

    def generate(
        self,
        conferences: list[Conference],
        filename: str = "2026-H2-conferences.md",
    ) -> Path:
        stats = self._compute_stats(conferences)
        context = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stats": stats,
            "conferences": [self._prepare_conference(c) for c in conferences],
        }

        content = self.template.render(**context)
        output_path = self.output_dir / filename
        output_path.write_text(content, encoding="utf-8")
        logger.info("Report written to %s", output_path)
        return output_path

    def _compute_stats(self, conferences: list[Conference]) -> dict[str, Any]:
        total_domestic = 0
        institution_counter: Counter[str] = Counter()

        for conf in conferences:
            domestic = conf.domestic_papers()
            total_domestic += len(domestic)
            for paper in domestic:
                for author in paper.authors:
                    for aff in author.affiliations:
                        normalized = self.matcher.normalize(aff)
                        if self.matcher.is_domestic(normalized):
                            institution_counter[normalized] += 1

        institution_stats = [
            {"institution": inst, "count": count}
            for inst, count in institution_counter.most_common(20)
        ]

        return {
            "total_conferences": len(conferences),
            "total_collected_papers": sum(len(c.papers) for c in conferences),
            "total_domestic_papers": total_domestic,
            "institution_stats": institution_stats,
        }

    def _prepare_conference(self, conf: Conference) -> dict[str, Any]:
        domestic_papers = conf.domestic_papers()

        # 最新论文（按 arXiv 提交时间倒序，取前 15 篇）
        recent_papers = sorted(
            conf.papers,
            key=lambda p: p.paper_id or "",
            reverse=True,
        )[:15]

        return {
            "display_name": conf.display_name,
            "date_range": conf.date_range,
            "location": conf.location,
            "website": conf.website,
            "domain": conf.domain,
            "collected_count": len(conf.papers),
            "domestic_count": len(domestic_papers),
            "domestic_papers": [self._prepare_paper(p) for p in domestic_papers],
            "recent_papers": [self._prepare_recent_paper(p) for p in recent_papers],
        }

    def _prepare_paper(self, paper: Paper) -> dict[str, Any]:
        domestic_authors = []
        for author in paper.authors:
            domestic_affs = []
            for aff in author.affiliations:
                normalized = self.matcher.normalize(aff)
                if self.matcher.is_domestic(normalized):
                    domestic_affs.append(normalized)
            if domestic_affs:
                domestic_authors.append(
                    {
                        "name": author.name,
                        "chinese_name": author.chinese_name,
                        "affiliation": "，".join(domestic_affs),
                    }
                )

        return {
            "title": paper.title,
            "arxiv_id": paper.paper_id or "",
            "url": paper.url or "",
            "abstract": paper.abstract or "",
            "domestic_authors": domestic_authors,
        }

    def _prepare_recent_paper(self, paper: Paper) -> dict[str, Any]:
        author_names = [a.name for a in paper.authors[:5]]
        if len(paper.authors) > 5:
            author_names.append("et al.")
        return {
            "title": paper.title,
            "arxiv_id": paper.paper_id or "",
            "url": paper.url or "",
            "authors": ", ".join(author_names),
            "abstract": (paper.abstract or "")[:200],
        }
