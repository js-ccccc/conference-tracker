"""Markdown 报告生成器"""

from __future__ import annotations

import logging
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
        per_conference = []
        total_domestic = 0
        tsinghua_total = 0
        peking_total = 0

        for conf in conferences:
            domestic = conf.domestic_papers()
            tsinghua = conf.tsinghua_papers()
            peking = conf.peking_papers()

            total_domestic += len(domestic)
            tsinghua_total += len(tsinghua)
            peking_total += len(peking)

            per_conference.append(
                {
                    "abbr": conf.abbr,
                    "tsinghua": len(tsinghua),
                    "peking": len(peking),
                    "domestic": len(domestic),
                }
            )

        return {
            "total_conferences": len(conferences),
            "total_domestic_papers": total_domestic,
            "tsinghua_total": tsinghua_total,
            "peking_total": peking_total,
            "per_conference": per_conference,
        }

    def _prepare_conference(self, conf: Conference) -> dict[str, Any]:
        highlighted = conf.highlighted_papers()
        other_domestic = [
            p for p in conf.domestic_papers() if not (p.has_tsinghua or p.has_peking)
        ]

        return {
            "display_name": conf.display_name,
            "date_range": conf.date_range,
            "location": conf.location,
            "website": conf.website,
            "domain": conf.domain,
            "ccf_rating": conf.ccf_rating,
            "submission_deadline": conf.submission_deadline,
            "notification_date": conf.notification_date,
            "domestic_count": len(conf.domestic_papers()),
            "tsinghua_count": len(conf.tsinghua_papers()),
            "peking_count": len(conf.peking_papers()),
            "highlighted_papers": [self._prepare_paper(p) for p in highlighted],
            "other_domestic_papers": [self._prepare_paper(p) for p in other_domestic],
        }

    def _prepare_paper(self, paper: Paper) -> dict[str, Any]:
        authors_display = ", ".join(
            self.matcher.format_author_display(a) for a in paper.authors
        )
        all_affs: list[str] = []
        for author in paper.authors:
            for aff in author.affiliations:
                if aff and aff not in all_affs:
                    all_affs.append(aff)

        return {
            "title": paper.title,
            "authors_display": authors_display or "未知",
            "affiliations_display": "，".join(all_affs) if all_affs else "未知",
            "url": paper.url,
            "award": paper.award,
        }
