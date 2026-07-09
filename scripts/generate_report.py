"""从缓存快速重新生成报告"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cache import CacheManager
from src.config_loader import load_conferences, load_institutions, load_settings
from src.generator import ReportGenerator
from src.models import Conference
from src.processor import DataProcessor


def main():
    settings = load_settings()
    institutions = load_institutions()
    output_cfg = settings.get("output", {})

    cache = CacheManager(output_cfg.get("cache_dir", "data"))
    processor = DataProcessor(institutions, load_settings())

    conferences = []
    for cfg in load_conferences():
        cached = cache.load_conference(cfg["id"])
        conferences.append(cached if cached else Conference.from_config(cfg))

    conferences.sort(key=lambda c: c.date_start)

    generator = ReportGenerator(
        matcher=processor.institution_matcher,
        output_dir=output_cfg.get("report_dir", "reports"),
    )
    path = generator.generate(
        conferences,
        filename=output_cfg.get("report_filename", "2026-H2-conferences.md"),
    )
    print(f"Report: {path}")


if __name__ == "__main__":
    main()
