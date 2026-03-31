"""Vercel serverless function - 이미지 분석 + 작업지시서 생성."""

from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler


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

COMPLEXITY_KR = {"low": "단순", "medium": "보통", "high": "복잡"}


def _parse_json_response(text: str) -> dict:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text.strip())


def _normalize_size(size_value) -> float:
    if isinstance(size_value, (int, float)):
        return float(size_value)
    if isinstance(size_value, dict):
        return float(max(size_value.values()))
    if isinstance(size_value, str):
        nums = re.findall(r"[\d.]+", size_value)
        return float(nums[0]) if nums else 10.0
    return 10.0


def analyze_and_generate(image_b64: str, media_type: str, client_name: str) -> dict:
    """이미지 분석 + 작업지시서 데이터 생성."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_b64,
            },
        },
        {"type": "text", "text": ANALYSIS_PROMPT},
    ]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )

    data = _parse_json_response(response.content[0].text)

    # Normalize
    analysis = {
        "product_type": data.get("product_type", "기타"),
        "fabric_type": data.get("fabric_type", "해당없음"),
        "fabric_texture": data.get("fabric_texture", ""),
        "primary_colors": data.get("primary_colors", []),
        "secondary_colors": data.get("secondary_colors", []),
        "size_estimate_cm": _normalize_size(data.get("size_estimate_cm", 10.0)),
        "complexity": data.get("complexity", "medium"),
        "complexity_kr": COMPLEXITY_KR.get(data.get("complexity", "medium"), "보통"),
        "has_embroidery": bool(data.get("has_embroidery", False)),
        "has_costume": bool(data.get("has_costume", False)),
        "has_accessories": bool(data.get("has_accessories", False)),
        "eye_type": data.get("eye_type", "해당없음"),
        "notes": data.get("notes", ""),
    }

    # Color matches (all PENDING for now)
    all_colors = analysis["primary_colors"] + analysis["secondary_colors"]
    color_matches = []
    for c in all_colors:
        is_primary = c in analysis["primary_colors"]
        color_matches.append({
            "color_name": c,
            "category": "주요" if is_primary else "보조",
            "merida_code": None,
            "suggested_page": None,
        })

    return {
        "client_name": client_name,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "analysis": analysis,
        "color_matches": color_matches,
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length))

            image_b64 = body["image_b64"]
            media_type = body.get("media_type", "image/jpeg")
            client_name = body.get("client_name", "미지정")

            result = analyze_and_generate(image_b64, media_type, client_name)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
