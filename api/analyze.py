"""Vercel serverless function - 이미지 분석 + 작업지시서 생성."""

import json
import os
import re
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler

import anthropic

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
  "size_estimate_cm": 10,
  "complexity": "low/medium/high",
  "has_embroidery": false,
  "has_costume": false,
  "has_accessories": false,
  "eye_type": "자수눈/플라스틱눈/프린트눈/단추눈/비즈눈/해당없음 중 택1",
  "notes": "기타 제조 관련 특이사항"
}

색상은 한국어로 구체적으로 작성하세요 (예: 흰색, 연분홍, 진갈색).
primary_colors: 면적이 가장 넓은 주요 색상 (1~3개)
secondary_colors: 포인트/디테일 색상 (0~5개)
complexity: low=단순형태 2색이하, medium=보통 3~4색, high=복잡 5색이상 코스튬 자수\
"""

COMPLEXITY_KR = {"low": "단순", "medium": "보통", "high": "복잡"}


def _parse_json_response(text):
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text.strip())


def _normalize_size(size_value):
    if isinstance(size_value, (int, float)):
        return float(size_value)
    if isinstance(size_value, dict):
        return float(max(size_value.values()))
    if isinstance(size_value, str):
        nums = re.findall(r"[\d.]+", size_value)
        return float(nums[0]) if nums else 10.0
    return 10.0


def analyze_and_generate(image_b64, media_type, client_name):
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_b64,
                    },
                },
                {"type": "text", "text": ANALYSIS_PROMPT},
            ],
        }],
    )

    data = _parse_json_response(response.content[0].text)

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

    all_colors = analysis["primary_colors"] + analysis["secondary_colors"]
    color_matches = []
    for c in all_colors:
        color_matches.append({
            "color_name": c,
            "category": "주요" if c in analysis["primary_colors"] else "보조",
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
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))

            result = analyze_and_generate(
                body["image_b64"],
                body.get("media_type", "image/jpeg"),
                body.get("client_name", "미지정"),
            )

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

        except Exception as e:
            tb = traceback.format_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(
                {"error": str(e), "traceback": tb}, ensure_ascii=False
            ).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
