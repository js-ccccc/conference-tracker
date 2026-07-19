"""中文名推断模块"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.models import Author

logger = logging.getLogger(__name__)

# 常见英文拼音 -> 中文姓氏映射（覆盖常见姓氏）
PINYIN_SURNAME_MAP: dict[str, str] = {
    "li": "李", "wang": "王", "zhang": "张", "liu": "刘", "chen": "陈",
    "yang": "杨", "huang": "黄", "zhao": "赵", "wu": "吴", "zhou": "周",
    "xu": "徐", "sun": "孙", "ma": "马", "zhu": "朱", "hu": "胡",
    "guo": "郭", "he": "何", "gao": "高", "lin": "林", "luo": "罗",
    "zheng": "郑", "liang": "梁", "xie": "谢", "song": "宋", "tang": "唐",
    "han": "韩", "feng": "冯", "deng": "邓", "cao": "曹", "peng": "彭",
    "zeng": "曾", "xiao": "肖", "tian": "田", "dong": "董", "yuan": "袁",
    "pan": "潘", "yu": "于", "jiang": "蒋", "cai": "蔡", "yu2": "余",
    "du": "杜", "ye": "叶", "cheng": "程", "su": "苏", "wei": "魏",
    "lu": "陆", "ren": "任", "shen": "沈", "yao": "姚", "lu2": "卢",
    "jiang2": "姜", "cui": "崔", "zhong": "钟", "tan": "谭", "lu3": "陆",
    "wang2": "汪", "ren2": "任", "fan": "范", "jin": "金", "shi": "石",
    "jia": "贾", "wei2": "韦", "qiu": "邱", "xia": "夏", "hou": "侯",
    "fang": "方", "zou": "邹", "xiong": "熊", "bai": "白", "meng": "孟",
    "qin": "秦", "gu": "顾", "mao": "毛", "hao": "郝", "long": "龙",
    "wan": "万", "duan": "段", "lei": "雷", "qian": "钱", "tang2": "汤",
    "yin": "尹", "li3": "黎", "yi": "易", "chang": "常", "wu2": "武",
    "qiao": "乔", "he2": "贺", "la": "赖", "gong": "龚", "wen": "文",
}

# 常见英文名 -> 中文名映射（知名学者库，可扩展）
KNOWN_NAME_MAP: dict[str, str] = {
    "jianlin": "林剑林",
    "wei zhang": "张炜",
    "jiwei li": "李继伟",
    "yann lecun": "杨立昆",
    "andrew ng": "吴恩达",
    "fei-fei li": "李飞飞",
}


class ChineseNameResolver:
    """根据英文名推断作者中文名"""

    def __init__(self, settings: dict[str, Any]):
        resolver_cfg = settings.get("chinese_name", {})
        self.enabled = resolver_cfg.get("enabled", True)
        self.confidence_threshold = resolver_cfg.get("confidence_threshold", 0.7)
        self.surname_map = {**PINYIN_SURNAME_MAP, **resolver_cfg.get("surname_map", {})}
        self.known_map = {**KNOWN_NAME_MAP, **resolver_cfg.get("known_names", {})}

    def resolve(self, author: Author) -> str | None:
        if not self.enabled or not author.name:
            return None

        name = author.name.strip()
        if self._is_chinese(name):
            return name

        key = name.lower()
        if key in self.known_map:
            return self.known_map[key]

        return self._infer_from_pinyin(name)

    def resolve_authors(self, authors: list[Author]) -> None:
        if not self.enabled:
            return

        resolved = 0
        for author in authors:
            if author.chinese_name:
                continue
            chinese = self.resolve(author)
            if chinese:
                author.chinese_name = chinese
                resolved += 1

        if resolved:
            logger.info("Chinese name resolved for %d authors", resolved)

    @staticmethod
    def _is_chinese(text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text))

    def _infer_from_pinyin(self, name: str) -> str | None:
        parts = re.split(r"[\s\-,.]+", name.strip())
        parts = [p.lower() for p in parts if p]

        if not parts:
            return None

        # 西方姓名格式：Given Family 或 Family, Given
        # 华人学者常用：Pinyin Given + Pinyin Surname，或 Surname + Given
        # 取最后一个 token 作为姓氏候选（英文习惯 Family 在后）
        # 也尝试第一个 token（中文习惯 Surname 在前）
        candidates = []
        if len(parts) >= 2:
            candidates.append(parts[-1])  # Family name (Western order)
            candidates.append(parts[0])  # Surname (Chinese order)

        for candidate in candidates:
            surname = self.surname_map.get(candidate)
            if surname:
                # 推断中文名：姓氏 + 拼音名（无法精确反查，仅返回姓氏 + 原拼音名）
                given_parts = [p for p in parts if p != candidate]
                if given_parts:
                    given = " ".join(given_parts).title()
                    return f"{surname}{given}（推断）"
                return f"{surname}（推断）"

        return None
