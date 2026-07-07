"""配置加载工具"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


def load_yaml(filename: str) -> dict[str, Any]:
    path = CONFIG_DIR / filename
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_conferences() -> list[dict[str, Any]]:
    data = load_yaml("conferences.yaml")
    return data.get("conferences", [])


def load_institutions() -> dict[str, Any]:
    return load_yaml("institutions.yaml")


def load_settings() -> dict[str, Any]:
    return load_yaml("settings.yaml")


def get_project_root() -> Path:
    return PROJECT_ROOT
