"""HAPE 작업지시서 생성기 - CLI 진입점.

사용법:
    python main.py --image product_photo.jpg --client "금볕 주식회사"
    python main.py --image product_photo.jpg --output-format markdown
    python main.py --image product_photo.jpg --output work_order.html
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

# Windows cp949 인코딩 문제 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from analyzer import analyze_image
from color_matcher import match_colors
from models import WorkOrder
from work_order import generate

SUPPORTED_FORMATS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def load_image(path: str) -> tuple[bytes, str]:
    """이미지 파일 로드 → (bytes, media_type)."""
    p = Path(path)
    if not p.exists():
        print(f"오류: 이미지 파일을 찾을 수 없습니다: {path}", file=sys.stderr)
        sys.exit(1)
    ext = p.suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        print(
            f"오류: 지원하지 않는 이미지 형식입니다: {ext}\n"
            f"지원 형식: {', '.join(SUPPORTED_FORMATS.keys())}",
            file=sys.stderr,
        )
        sys.exit(1)
    return p.read_bytes(), SUPPORTED_FORMATS[ext]


def main():
    parser = argparse.ArgumentParser(
        description="HAPE 작업지시서 생성기 - 제품 이미지 분석 후 작업지시서 자동 생성",
    )
    parser.add_argument(
        "--image", required=True, help="제품 이미지 파일 경로 (jpg, png, webp, gif)",
    )
    parser.add_argument(
        "--client", default="미지정", help="클라이언트/브랜드명 (기본: 미지정)",
    )
    parser.add_argument(
        "--output-format",
        choices=["html", "markdown"],
        default="html",
        help="출력 형식 (기본: html)",
    )
    parser.add_argument(
        "--output", default=None, help="출력 파일 경로 (미지정 시 stdout)",
    )
    args = parser.parse_args()

    # API 키 확인
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "오류: ANTHROPIC_API_KEY 환경변수를 설정하세요.\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...",
            file=sys.stderr,
        )
        sys.exit(1)

    # 이미지 로드
    print(f"이미지 로드 중: {args.image}")
    image_bytes, media_type = load_image(args.image)
    print(f"  크기: {len(image_bytes):,} bytes, 형식: {media_type}")

    # Claude API 이미지 분석
    print("Claude API로 이미지 분석 중...")
    try:
        analysis = analyze_image(image_bytes, media_type)
    except Exception as e:
        print(f"오류: 이미지 분석 실패 - {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  제품: {analysis.product_type}")
    print(f"  원단: {analysis.fabric_type} ({analysis.fabric_texture})")
    print(f"  복잡도: {analysis.complexity}")
    print(f"  색상: {', '.join(analysis.primary_colors + analysis.secondary_colors)}")

    # 색상 매칭
    all_colors = analysis.primary_colors + analysis.secondary_colors
    color_matches = match_colors(all_colors)

    # 작업지시서 생성
    wo = WorkOrder(
        client_name=args.client,
        analysis=analysis,
        color_matches=color_matches,
        image_path=args.image,
    )

    output = generate(wo, fmt=args.output_format)

    # 출력
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"\n작업지시서 저장 완료: {args.output}")
    else:
        print("\n" + "=" * 60)
        print(output)


if __name__ == "__main__":
    main()
