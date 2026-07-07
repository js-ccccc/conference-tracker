"""数据缓存与增量更新"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.models import Conference, Paper

logger = logging.getLogger(__name__)


class CacheManager:
    """缓存已采集数据，支持增量更新"""

    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, conference_id: str) -> Path:
        return self.cache_dir / f"{conference_id}.json"

    def load(self, conference_id: str) -> dict[str, Any] | None:
        path = self._cache_path(conference_id)
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load cache for %s: %s", conference_id, exc)
            return None

    def save(self, conference: Conference) -> None:
        path = self._cache_path(conference.id)
        data = conference.to_dict()
        data["_cached_at"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Cached data for %s", conference.id)

    def load_conference(self, conference_id: str) -> Conference | None:
        data = self.load(conference_id)
        if not data:
            return None
        data.pop("_cached_at", None)
        return Conference.from_dict(data)

    def needs_update(
        self, conference_id: str, incremental: bool, force: bool = False
    ) -> bool:
        if force or not incremental:
            return True
        cached = self.load(conference_id)
        if not cached:
            return True
        papers = cached.get("papers", [])
        return len(papers) == 0

    def merge_papers(
        self, cached_papers: list[Paper], new_papers: list[Paper]
    ) -> list[Paper]:
        from src.processor.deduplicator import Deduplicator

        dedup = Deduplicator()
        return dedup.deduplicate(cached_papers + new_papers)
