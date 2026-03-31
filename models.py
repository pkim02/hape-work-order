"""HAPE 작업지시서 — 데이터 모델."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProductAnalysis:
    """Claude API 이미지 분석 결과."""

    product_type: str          # 키링, 인형, 파우치, 에코백, 쿠션, 바디필로우, 담요, 기타
    fabric_type: str           # 단모/장모/극세사/벨보아/면/폴리/해당없음
    fabric_texture: str        # 부드러운, 보들보들, 매끄러운, 뻣뻣한, etc.
    primary_colors: list[str] = field(default_factory=list)   # ["흰색", "연분홍"]
    secondary_colors: list[str] = field(default_factory=list) # ["검정", "빨강"]
    size_estimate_cm: float = 10.0
    complexity: str = "medium"  # low / medium / high
    has_embroidery: bool = False
    has_costume: bool = False
    has_accessories: bool = False
    eye_type: str = "해당없음"  # 자수눈/플라스틱눈/프린트눈/단추눈/비즈눈/해당없음
    notes: str = ""


@dataclass
class ColorMatch:
    """색상 → 메리다 컬러북 매칭 결과."""

    original_color: str
    color_name: str
    merida_code: str | None = None      # None = PENDING
    suggested_page: int | None = None   # None = PENDING


@dataclass
class WorkOrder:
    """최종 작업지시서 데이터."""

    client_name: str
    analysis: ProductAnalysis
    color_matches: list[ColorMatch] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    image_path: str = ""
