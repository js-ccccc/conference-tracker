"""数据采集器基类"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

import requests

from src.models import Conference, Paper

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """通用爬虫基类：请求头、频率控制、异常重试"""

    def __init__(self, settings: dict[str, Any]):
        collector_cfg = settings.get("collector", {})
        self.request_delay = collector_cfg.get("request_delay", 1.0)
        self.max_retries = collector_cfg.get("max_retries", 3)
        self.timeout = collector_cfg.get("timeout", 30)
        self.user_agent = collector_cfg.get(
            "user_agent", "ConferenceTracker/1.0 (Academic Research)"
        )
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        self._last_request_time = 0.0

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self._last_request_time = time.time()

    def get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> Optional[requests.Response]:
        for attempt in range(1, self.max_retries + 1):
            try:
                self._rate_limit()
                response = self.session.get(
                    url, params=params, headers=headers, timeout=self.timeout
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                logger.warning(
                    "Request failed (attempt %d/%d): %s - %s",
                    attempt,
                    self.max_retries,
                    url,
                    exc,
                )
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
        return None

    @abstractmethod
    def collect(self, conference: Conference, source_config: dict) -> list[Paper]:
        """采集指定会议的论文列表"""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...
