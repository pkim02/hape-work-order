"""메리다 컬러북 색상 매칭 (placeholder).

현재는 모든 색상에 PENDING을 반환합니다.
메리다 컬러북 데이터가 도착하면 data/merida_colors.json에 채워 넣으면
자동으로 매칭이 활성화됩니다.

Expected merida_colors.json schema:
{
    "흰색": {"code": "M-001", "page": 3},
    "검정": {"code": "M-002", "page": 3},
    "연분홍": {"code": "M-045", "page": 12},
    ...
}
"""

from __future__ import annotations

import json
from pathlib import Path

from models import ColorMatch

DATA_DIR = Path(__file__).parent / "data"


def _load_merida_colors() -> dict:
    path = DATA_DIR / "merida_colors.json"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) and data else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


MERIDA_COLORS: dict = _load_merida_colors()


def match_color(color_description: str) -> ColorMatch:
    """단일 색상을 메리다 컬러북에 매칭."""
    if MERIDA_COLORS and color_description in MERIDA_COLORS:
        entry = MERIDA_COLORS[color_description]
        return ColorMatch(
            original_color=color_description,
            color_name=color_description,
            merida_code=entry.get("code"),
            suggested_page=entry.get("page"),
        )

    return ColorMatch(
        original_color=color_description,
        color_name=color_description,
        merida_code=None,
        suggested_page=None,
    )


def match_colors(color_descriptions: list[str]) -> list[ColorMatch]:
    """색상 목록을 메리다 컬러북에 매칭."""
    return [match_color(c) for c in color_descriptions]
