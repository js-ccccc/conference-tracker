#!/usr/bin/env python3
"""
2026年下半年计算机顶会信息搜集 Agent

用法:
  python main.py                    # 增量更新全部会议
  python main.py --full             # 全量采集
  python main.py --conference icml-2026  # 指定会议
  python main.py --full --push      # 全量采集并推送至 GitHub
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.cache import CacheManager
from src.collector import CollectorManager
from src.config_loader import (
    get_project_root,
    load_conferences,
    load_institutions,
    load_settings,
)
from src.generator import ReportGenerator
from src.models import Conference
from src.processor import DataProcessor
from src.sync import GitSync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("conference-tracker")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="2026年下半年计算机顶会信息搜集 Agent"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="全量采集（默认增量更新）",
    )
    parser.add_argument(
        "--conference",
        type=str,
        default=None,
        help="仅采集指定会议 ID，如 icml-2026",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="采集完成后自动提交并推送至 GitHub",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="跳过报告生成",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新采集（忽略缓存）",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="跳过机构信息补全（加快速度）",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="强制开启机构信息补全（覆盖配置文件）",
    )
    return parser.parse_args()


def filter_conferences(
    all_configs: list[dict], conference_id: str | None
) -> list[dict]:
    if not conference_id:
        return all_configs
    filtered = [c for c in all_configs if c["id"] == conference_id]
    if not filtered:
        available = ", ".join(c["id"] for c in all_configs)
        logger.error("Conference '%s' not found. Available: %s", conference_id, available)
        sys.exit(1)
    return filtered


def run(args: argparse.Namespace) -> None:
    settings = load_settings()

    # --enrich 覆盖配置文件，强制开启补全
    if args.enrich:
        settings.setdefault("enrichment", {})["enabled"] = True
        logger.info("Enrichment force-enabled via --enrich flag")

    institutions = load_institutions()
    conf_configs = filter_conferences(load_conferences(), args.conference)

    output_cfg = settings.get("output", {})
    cache_dir = get_project_root() / output_cfg.get("cache_dir", "data")
    report_dir = get_project_root() / output_cfg.get("report_dir", "reports")
    report_filename = output_cfg.get("report_filename", "2026-H2-conferences.md")

    collector_mgr = CollectorManager(settings)
    processor = DataProcessor(institutions, settings)
    cache = CacheManager(cache_dir)
    incremental = not args.full

    conferences: list[Conference] = []

    # 确定是否补全：--no-enrich 优先级最高，其次 --enrich，最后配置文件
    do_enrich = (not args.no_enrich) and (args.enrich or settings.get("enrichment", {}).get("enabled", False))

    for conf_cfg in conf_configs:
        conference = Conference.from_config(conf_cfg)
        logger.info("Processing %s (%s)...", conference.abbr, conference.id)

        if not cache.needs_update(conference.id, incremental, force=args.force):
            cached = cache.load_conference(conference.id)
            if cached:
                logger.info("Using cached data for %s", conference.abbr)
                conferences.append(cached)
                continue

        raw_papers = collector_mgr.collect_all(conference, conf_cfg)
        if not raw_papers:
            cached = cache.load_conference(conference.id)
            if cached and cached.papers:
                logger.warning(
                    "Collection returned 0 papers for %s, keeping cached %d papers",
                    conference.abbr,
                    len(cached.papers),
                )
                conferences.append(cached)
                continue

        processed = processor.process_conference(
            conference, raw_papers, enrich=do_enrich
        )

        if incremental and not args.force:
            cached = cache.load_conference(conference.id)
            if cached and cached.papers:
                processed.papers = cache.merge_papers(
                    cached.papers, processed.papers
                )
                processed.papers = processor.process_papers(
                    processed.papers, enrich=do_enrich
                )

        if not processed.papers:
            cached = cache.load_conference(conference.id)
            if cached and cached.papers:
                logger.warning(
                    "Skipping empty save for %s, keeping %d cached papers",
                    conference.abbr,
                    len(cached.papers),
                )
                conferences.append(cached)
                continue

        cache.save(processed)
        conferences.append(processed)

    conferences.sort(key=lambda c: c.date_start)

    if not args.no_report:
        generator = ReportGenerator(
            matcher=processor.institution_matcher,
            output_dir=report_dir,
        )
        report_path = generator.generate(conferences, filename=report_filename)
        logger.info("Report generated: %s", report_path)

    if args.push:
        git_paths = [
            str(report_dir),
            str(cache_dir),
        ]
        commit_msg = (
            f"Auto update: {datetime.now().strftime('%Y-%m-%d')} "
            f"({len(conferences)} conferences)"
        )
        _git_commit_and_push(git_paths, commit_msg)

    logger.info("Done. Processed %d conferences.", len(conferences))


def _git_commit_and_push(paths: list[str], message: str) -> None:
    """通过 git 命令提交，避免修改全局 git config"""
    root = get_project_root()
    user_name = os.environ.get("GIT_USER_NAME", "github-actions[bot]")
    user_email = os.environ.get(
        "GIT_USER_EMAIL", "github-actions[bot]@users.noreply.github.com"
    )

    for path in paths:
        rel = Path(path).relative_to(root)
        subprocess.run(["git", "add", str(rel)], cwd=root, check=False)

    result = subprocess.run(
        ["git", "diff", "--staged", "--quiet"],
        cwd=root,
        capture_output=True,
    )
    if result.returncode == 0:
        logger.info("No changes to commit")
        return

    subprocess.run(
        [
            "git",
            "-c",
            f"user.name={user_name}",
            "-c",
            f"user.email={user_email}",
            "commit",
            "-m",
            message,
        ],
        cwd=root,
        check=True,
    )
    logger.info("Committed: %s", message)

    push = subprocess.run(["git", "push"], cwd=root, capture_output=True, text=True)
    if push.returncode != 0:
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            remote = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=root,
                capture_output=True,
                text=True,
            )
            if remote.returncode == 0:
                url = remote.stdout.strip()
                if url.startswith("https://") and "@" not in url:
                    authed_url = url.replace(
                        "https://", f"https://x-access-token:{token}@"
                    )
                    push = subprocess.run(
                        ["git", "push", authed_url, "HEAD"],
                        cwd=root,
                        capture_output=True,
                        text=True,
                    )
        if push.returncode != 0:
            logger.warning("Git push failed: %s", push.stderr)
        else:
            logger.info("Pushed to remote")
    else:
        logger.info("Pushed to remote")


if __name__ == "__main__":
    run(parse_args())
