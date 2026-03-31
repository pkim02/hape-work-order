"""Claude API 이미지 분석 — 제품 사진에서 작업지시서 정보 추출."""

from __future__ import annotations

import base64
import json
import re

import anthropic

from models import ProductAnalysis

MODEL = "claude-haiku-4-5-20251001"

ANALYSIS_PROMPT = """\
당신은 캐릭터 굿즈(인형, 키링, 파우치 등) 제조 전문가입니다.
이 제품 이미지를 분석하여 작업지시서에 필요한 정보를 추출하세요.

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트를 포함하지 마세요.

{
  "product_type": "키링/인형/파우치/에코백/쿠션/바디필로우/담요/뱃지/피규어/기타 중 택1",
  "fabric_type": "단모/장모/극세사/벨보아/밍크/면/폴리/해당없음 중 택1 또는 복수 기재",
  "fabric_texture": "원단 촉감/질감 설명 (예: 부드러운, 보들보들, 매끄러운, 뻣뻣한, 폭신한)",
  "primary_colors": ["주요 색상1", "주요 색상2"],
  "secondary_colors": ["보조/포인트 색상1", "보조 색상2"],
  "size_estimate_cm": 가장_긴_변_추정치_숫자,
  "complexity": "low/medium/high",
  "has_embroidery": true또는false,
  "has_costume": true또는false,
  "has_accessories": true또는false,
  "eye_type": "자수눈/플라스틱눈/프린트눈/단추눈/비즈눈/해당없음 중 택1",
  "notes": "기타 제조 관련 특이사항 (꼬리, 날개, 특수 부자재, 충전재 등)"
}

색상 작성 규칙:
- 한국어로 구체적으로 작성 (예: 흰색, 연분홍, 진갈색, 하늘색, 크림색)
- primary_colors: 면적이 가장 넓은 주요 색상 (1~3개)
- secondary_colors: 포인트/디테일 색상 (0~5개)

complexity 기준:
- low: 단순 형태, 2색 이하, 자수/코스튬 없음
- medium: 보통 형태, 3~4색, 간단한 자수 있을 수 있음
- high: 복잡한 형태, 5색 이상, 코스튬/정교한 자수/다수 부자재

봉제 제품이 아닌 경우 (아크릴, PVC 등):
- fabric_type: "해당없음"
- fabric_texture: 재질 설명 (예: 아크릴, PVC, 실리콘)\
"""


def _parse_json_response(text: str) -> dict:
    """LLM 응답에서 JSON 블록 추출."""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text.strip())


def _normalize_size(size_value) -> float:
    """size_estimate_cm 타입 방어 (dict, string, number)."""
    if isinstance(size_value, (int, float)):
        return float(size_value)
    if isinstance(size_value, dict):
        return float(max(size_value.values()))
    if isinstance(size_value, str):
        nums = re.findall(r"[\d.]+", size_value)
        return float(nums[0]) if nums else 10.0
    return 10.0


def _dict_to_analysis(data: dict) -> ProductAnalysis:
    """JSON dict → ProductAnalysis 변환."""
    return ProductAnalysis(
        product_type=data.get("product_type", "기타"),
        fabric_type=data.get("fabric_type", "해당없음"),
        fabric_texture=data.get("fabric_texture", ""),
        primary_colors=data.get("primary_colors", []),
        secondary_colors=data.get("secondary_colors", []),
        size_estimate_cm=_normalize_size(data.get("size_estimate_cm", 10.0)),
        complexity=data.get("complexity", "medium"),
        has_embroidery=bool(data.get("has_embroidery", False)),
        has_costume=bool(data.get("has_costume", False)),
        has_accessories=bool(data.get("has_accessories", False)),
        eye_type=data.get("eye_type", "해당없음"),
        notes=data.get("notes", ""),
    )


def analyze_image(image_bytes: bytes, media_type: str) -> ProductAnalysis:
    """제품 이미지를 Claude Haiku 4.5로 분석하여 ProductAnalysis 반환."""
    client = anthropic.Anthropic()

    content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(image_bytes).decode(),
            },
        },
        {"type": "text", "text": ANALYSIS_PROMPT},
    ]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )

    response_text = response.content[0].text

    # 1차 파싱 시도
    try:
        data = _parse_json_response(response_text)
        return _dict_to_analysis(data)
    except (json.JSONDecodeError, KeyError, IndexError):
        pass

    # 2차 시도: 재요청
    retry_content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(image_bytes).decode(),
            },
        },
        {
            "type": "text",
            "text": ANALYSIS_PROMPT + "\n\nJSON 형식으로만 응답하세요. 다른 텍스트를 포함하지 마세요.",
        },
    ]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": retry_content}],
    )

    data = _parse_json_response(response.content[0].text)
    return _dict_to_analysis(data)
