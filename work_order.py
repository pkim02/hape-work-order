"""작업지시서 생성 — HTML 및 Markdown 출력."""

from __future__ import annotations

from pathlib import Path

import jinja2

from models import WorkOrder

TEMPLATE_DIR = Path(__file__).parent / "templates"

COMPLEXITY_KR = {"low": "단순", "medium": "보통", "high": "복잡"}


def _bool_kr(value: bool) -> str:
    return "있음" if value else "없음"


def generate_html(work_order: WorkOrder) -> str:
    """Jinja2 템플릿으로 HTML 작업지시서 생성."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )
    env.filters["bool_kr"] = _bool_kr
    env.filters["complexity_kr"] = lambda v: COMPLEXITY_KR.get(v, v)

    template = env.get_template("work_order.html")
    return template.render(
        wo=work_order,
        a=work_order.analysis,
        colors=work_order.color_matches,
    )


def generate_markdown(work_order: WorkOrder) -> str:
    """Markdown 작업지시서 생성."""
    a = work_order.analysis
    lines = [
        "# 작업지시서 (Work Order)",
        "",
        f"- **날짜:** {work_order.generated_at.strftime('%Y-%m-%d %H:%M')}",
        f"- **클라이언트:** {work_order.client_name}",
        f"- **이미지:** {work_order.image_path}",
        "",
        "---",
        "",
        "## 제품 정보 (Product Info)",
        "",
        f"| 항목 | 내용 |",
        f"|------|------|",
        f"| 제품 유형 | {a.product_type} |",
        f"| 예상 크기 | {a.size_estimate_cm} cm |",
        "",
        "## 원단 정보 (Fabric Info)",
        "",
        f"| 항목 | 내용 |",
        f"|------|------|",
        f"| 원단 종류 | {a.fabric_type} |",
        f"| 촉감/텍스처 | {a.fabric_texture} |",
        f"| 복잡도 | {COMPLEXITY_KR.get(a.complexity, a.complexity)} |",
        "",
        "## 색상 정보 (Color Info)",
        "",
        "| 구분 | 색상 | 메리다 코드 | 페이지 |",
        "|------|------|------------|--------|",
    ]

    for cm in work_order.color_matches:
        is_primary = cm.original_color in a.primary_colors
        label = "주요" if is_primary else "보조"
        code = cm.merida_code or "PENDING"
        page = str(cm.suggested_page) if cm.suggested_page else "-"
        lines.append(f"| {label} | {cm.color_name} | {code} | {page} |")

    lines += [
        "",
        "## 세부 사항 (Details)",
        "",
        f"| 항목 | 내용 |",
        f"|------|------|",
        f"| 눈 유형 | {a.eye_type} |",
        f"| 자수 | {_bool_kr(a.has_embroidery)} |",
        f"| 코스튬 | {_bool_kr(a.has_costume)} |",
        f"| 액세서리 | {_bool_kr(a.has_accessories)} |",
    ]

    if a.notes:
        lines += [
            "",
            "## 비고 (Notes)",
            "",
            a.notes,
        ]

    lines.append("")
    return "\n".join(lines)


def generate(work_order: WorkOrder, fmt: str = "html") -> str:
    """작업지시서 생성 (html 또는 markdown)."""
    if fmt == "markdown":
        return generate_markdown(work_order)
    return generate_html(work_order)
