from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "generated_images"
FONT_REGULAR = Path("C:/Windows/Fonts/malgun.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(str(path), size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, text_font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textbbox((0, 0), trial, font=text_font)[2] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_wrapped_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
                      text_font, fill: str, max_width: int, line_gap: int = 10) -> int:
    x, y = xy
    lines = []
    for raw_line in text.split("\n"):
        lines.extend(wrap_text(draw, raw_line, text_font, max_width))
    line_height = text_font.size + line_gap
    for idx, line in enumerate(lines):
        draw.text((x, y + idx * line_height), line, font=text_font, fill=fill)
    return y + len(lines) * line_height


def rounded_box(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
                fill: str, outline: str, radius: int = 24, width: int = 3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int],
          fill: str = "#3B82F6", width: int = 8):
    draw.line([start, end], fill=fill, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head = 20
    left = (
        end[0] - head * math.cos(angle - math.pi / 6),
        end[1] - head * math.sin(angle - math.pi / 6),
    )
    right = (
        end[0] - head * math.cos(angle + math.pi / 6),
        end[1] - head * math.sin(angle + math.pi / 6),
    )
    draw.polygon([end, left, right], fill=fill)


def add_header(draw: ImageDraw.ImageDraw, title: str, subtitle: str):
    draw.text((80, 52), title, font=font(44, bold=True), fill="#0F172A")
    draw.text((80, 116), subtitle, font=font(20), fill="#475569")


def add_metric_chip(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, value: str, color: str):
    rounded_box(draw, (x, y, x + 220, y + 92), fill="#FFFFFF", outline=color, radius=22, width=3)
    draw.text((x + 18, y + 16), label, font=font(18, bold=True), fill="#334155")
    draw.text((x + 18, y + 46), value, font=font(28, bold=True), fill=color)


def build_service_flow(project: dict, company: dict, out_path: Path):
    img = Image.new("RGB", (1600, 900), "#F8FAFC")
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 1600, 180), fill="#E0F2FE")
    add_header(
        draw,
        "MarketGate AI 서비스 운영 흐름도",
        "수출지원 공고 수집부터 기업 맞춤 추천·알림까지의 전체 서비스 흐름",
    )

    stages = [
        ("공고 수집", "KOTRA·중진공·지자체\n15개+ 기관 데이터 수집", "#DBEAFE", "#2563EB"),
        ("정형화·가공", "공고 원문 정리\n14개 핵심 필드 구조화", "#E0F2FE", "#0284C7"),
        ("AI 매칭", "HS Code·업종·수출이력 기반\n기업별 적합도 분석", "#DCFCE7", "#16A34A"),
        ("알림·리포트", "Top-5 공고 추천\n30분 내 알림·리포트 제공", "#FCE7F3", "#DB2777"),
    ]
    x_positions = [90, 450, 810, 1170]
    y0 = 290
    box_w = 280
    box_h = 210
    for idx, (title, body, fill, outline) in enumerate(stages):
        x = x_positions[idx]
        rounded_box(draw, (x, y0, x + box_w, y0 + box_h), fill=fill, outline=outline)
        draw.text((x + 24, y0 + 22), title, font=font(28, bold=True), fill="#0F172A")
        draw_wrapped_text(draw, (x + 24, y0 + 78), body, font(20), "#1E293B", box_w - 48, 8)
        if idx < len(stages) - 1:
            arrow(draw, (x + box_w, y0 + box_h // 2), (x_positions[idx + 1] - 20, y0 + box_h // 2))

    draw.text((90, 225), "핵심 프로세스", font=font(24, bold=True), fill="#0F172A")
    add_metric_chip(draw, 90, 585, "통합 기관", "15개+", "#2563EB")
    add_metric_chip(draw, 350, 585, "매칭 정확도", "87%", "#0F766E")
    add_metric_chip(draw, 610, 585, "탐색 시간", "8h → 30분", "#DB2777")
    add_metric_chip(draw, 870, 585, "추천 결과", "Top-5 자동 제공", "#7C3AED")

    footer = (
        f"{company['company']['name']} | {project['meta']['project_title']} | "
        "전문 공급기업 데이터 기반 공고 추천 자동화"
    )
    draw.text((80, 830), footer, font=font(18), fill="#475569")
    img.save(out_path)


def build_tech_arch(project: dict, out_path: Path):
    img = Image.new("RGB", (1600, 900), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 1600, 180), fill="#ECFDF5")
    add_header(
        draw,
        "공고 정형화 및 AI 매칭 기술 아키텍처",
        "데이터 수집·정형화·추천 API·알림 레이어를 기준으로 한 구현 구조",
    )

    layers = [
        ("데이터 수집 레이어", "크롤러 / API 연동 / 데이터 적재", "#DBEAFE", "#2563EB"),
        ("정형화 레이어", "Rule-based 파싱 / NLP 추출 / HS Code 매핑", "#E0F2FE", "#0284C7"),
        ("추천 엔진 레이어", "TF-IDF / Cosine Similarity / 가중치 보정", "#DCFCE7", "#16A34A"),
        ("서비스 제공 레이어", "추천 API / 대시보드 / 이메일·앱 알림", "#FEF3C7", "#D97706"),
    ]
    left = 220
    top = 240
    width = 1160
    height = 120
    gap = 28
    for idx, (title, body, fill, outline) in enumerate(layers):
        y = top + idx * (height + gap)
        rounded_box(draw, (left, y, left + width, y + height), fill=fill, outline=outline, radius=26)
        draw.text((left + 28, y + 20), title, font=font(28, bold=True), fill="#0F172A")
        draw.text((left + 28, y + 64), body, font=font(20), fill="#334155")
        if idx < len(layers) - 1:
            arrow(draw, (800, y + height), (800, y + height + gap - 6), fill=outline, width=7)

    add_metric_chip(draw, 220, 780, "정형 필드", "14개", "#0284C7")
    add_metric_chip(draw, 480, 780, "필드 완성도", "95%+", "#16A34A")
    add_metric_chip(draw, 740, 780, "HS Code 매핑", "90%+", "#2563EB")
    add_metric_chip(draw, 1000, 780, "처리 속도", "30초", "#D97706")
    img.save(out_path)


def build_kpi_roadmap(project: dict, out_path: Path):
    img = Image.new("RGB", (1600, 900), "#FFFDF8")
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 1600, 180), fill="#FFEDD5")
    add_header(
        draw,
        "KPI 목표 및 기대효과 로드맵",
        "단기·중기·장기 목표를 정량 지표 중심으로 정리한 제출용 인포그래픽",
    )

    stages = [
        ("단기 (6개월)", ["파일럿 30개사", "정확도 80% 이상", "탐색 시간 8h → 30분"], "#FDE68A", "#D97706"),
        ("중기 (12개월)", ["유료 기업 200개사", "월 매출 400만원", "추천 품질 87% 검증"], "#BFDBFE", "#2563EB"),
        ("장기 (24개월)", ["전국 지자체 100% 커버", "바이어 매칭 확장", "글로벌 데이터 연동"], "#DDD6FE", "#7C3AED"),
    ]
    x_positions = [90, 545, 1000]
    for idx, (title, bullets, fill, outline) in enumerate(stages):
        x = x_positions[idx]
        rounded_box(draw, (x, 280, x + 360, 520), fill=fill, outline=outline, radius=28)
        draw.text((x + 24, 305), title, font=font(30, bold=True), fill="#0F172A")
        y = 365
        for bullet in bullets:
            draw.text((x + 28, y), f"· {bullet}", font=font(22), fill="#1E293B")
            y += 58
        if idx < len(stages) - 1:
            arrow(draw, (x + 360, 400), (x_positions[idx + 1] - 22, 400), fill=outline)

    draw.text((90, 585), "핵심 정량 지표", font=font(24, bold=True), fill="#0F172A")
    add_metric_chip(draw, 90, 635, "매칭 정확도", "75% → 87% → 90%+", "#2563EB")
    add_metric_chip(draw, 390, 635, "업무 절감", "주 8h → 30분", "#DB2777")
    add_metric_chip(draw, 690, 635, "고객 확대", "30개사 → 200개사", "#16A34A")
    add_metric_chip(draw, 990, 635, "구독 매출", "월 400만원", "#D97706")

    footer = f"대상 과제: {project['meta']['project_title']}"
    draw.text((90, 835), footer, font=font(18), fill="#475569")
    img.save(out_path)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    project = load_json(DATA_DIR / "project_input.json")
    company = load_json(DATA_DIR / "company_master.json")

    build_service_flow(project, company, OUT_DIR / "marketgate_service_flow.png")
    build_tech_arch(project, OUT_DIR / "marketgate_tech_architecture.png")
    build_kpi_roadmap(project, OUT_DIR / "marketgate_kpi_roadmap.png")

    print("generated:")
    for path in sorted(OUT_DIR.glob("*.png")):
        print(path)


if __name__ == "__main__":
    main()
