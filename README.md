# HAPE 작업지시서 생성기

캐릭터 굿즈 제품 이미지를 분석하여 중국 공장용 작업지시서를 자동 생성합니다.

## 필수 조건

- Python 3.12+
- `anthropic` 패키지
- `jinja2` 패키지

```bash
pip install anthropic jinja2
```

## 설정

Anthropic API 키 환경변수 설정:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## 사용법

```bash
# 기본 (HTML 출력, stdout)
python main.py --image product_photo.jpg

# 클라이언트 지정 + 파일 저장
python main.py --image product_photo.jpg --client "금볕 주식회사" --output work_order.html

# Markdown 출력
python main.py --image product_photo.jpg --output-format markdown --output work_order.md
```

### CLI 옵션

| 옵션 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `--image` | O | - | 제품 이미지 파일 경로 |
| `--client` | X | 미지정 | 클라이언트/브랜드명 |
| `--output-format` | X | html | 출력 형식 (html/markdown) |
| `--output` | X | stdout | 출력 파일 경로 |

## 구조

```
작업지시서/
├── main.py              # CLI 진입점
├── analyzer.py          # Claude API 이미지 분석
├── color_matcher.py     # 메리다 컬러북 매칭 (placeholder)
├── work_order.py        # 작업지시서 HTML/Markdown 생성
├── models.py            # 데이터 모델 (dataclass)
├── templates/
│   └── work_order.html  # Jinja2 이메일 템플릿
└── data/
    └── merida_colors.json  # 메리다 컬러북 데이터 (추후 입력)
```

## 메리다 컬러북 연동

현재 색상 코드는 모두 `PENDING`으로 표시됩니다. 컬러북 데이터가 도착하면 `data/merida_colors.json`에 아래 형식으로 입력하세요:

```json
{
  "흰색": {"code": "M-001", "page": 3},
  "검정": {"code": "M-002", "page": 3},
  "연분홍": {"code": "M-045", "page": 12}
}
```

입력 후 별도 코드 수정 없이 자동으로 매칭이 활성화됩니다.
