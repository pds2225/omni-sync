"""
image_advisor.py — 이미지 슬롯 추천·위치 결정 에이전트
=======================================================
역할: project_input.json의 content를 분석하여 5개 슬롯에 이미지 추천 텍스트·위치 생성.
      assets에 실제 이미지 파일이 있으면 image_slots, 없으면 image_placeholders+blank_image_slots.

5개 슬롯 (우선순위 순):
    SLOT_OVERVIEW_IMG   (1-필수)  overview 표 [6,2] 셀
    SLOT_BM_FLOW        (2-권장)  '나. 비즈니스 모델 소개' 단락 뒤
    SLOT_TECH_ARCH      (2-권장)  '나. 데이터 상품 및 활용 서비스 필요성' 단락 뒤
    SLOT_EXPECTED_KPI   (2-권장)  '가. 기대효과' 단락 뒤
    SLOT_MARKET_CHART   (3-선택)  '1. 사업(과제) 개요' 단락 뒤

주요 인터페이스:
    ImageAdvisor(insert_threshold=2).run(content) -> content
        content["image_slots"]       : {slot_id: {path, table_index, row, cell, ...}}
        content["image_placeholders"]: {slot_id: {location, caption_text, ...}}
        content["blank_image_slots"] : [{para_keyword, title, height_cm, ...}]
        content["image_recommendations"]: 전체 추천 목록 (리포트용)
"""
from __future__ import annotations
import re
from typing import Any


# ════════════════════════════════════════════════════════════════
# 슬롯 정의 테이블
# ════════════════════════════════════════════════════════════════
# 각 슬롯은 "고정 위치 + 내용 분석 기반 추천 텍스트 생성" 방식
_SLOT_TEMPLATES = [
    # ─ SLOT 1 : 개요표 관련이미지 셀 (표 #3, 행6/7, 열2/3) ──────
    # 최우선 이미지 — 서비스/제품 전체 구조를 한눈에 보여주는 도식
    {
        "slot_id":     "SLOT_OVERVIEW_IMG",
        "location":    "table_cell",
        "table_index": 4,       # 원본 템플릿 기준 번호 (작성요령 삭제 전 STEP 2-B 실행)
        "row":         6,
        "cell":        2,
        "row2":        7,       # 제목 행 (caption row)
        "cell2":       2,
        "priority":    1,
        "category":    "service_flow",
        "title_key":   None,    # meta에서 동적 생성
        "hint":        (
            "Figma·Canva·draw.io 등으로 제작 권장.\n"
            "서비스 흐름(데이터 수집 → 가공 → AI 매칭 → 기업 알림)을 "
            "좌→우 화살표 플로우 차트로 표현하면 효과적."
        ),
    },
    # ─ SLOT 2 : 비즈니스 모델 소개 직후 ─────────────────────────
    # BM Canvas 또는 수익구조 다이어그램
    {
        "slot_id":     "SLOT_BM_FLOW",
        "location":    "after_paragraph",
        "para_keyword":"나. 비즈니스 모델 소개",
        "insert_offset": 2,     # 해당 단락의 내용 뒤 N번째 위치
        "blank_height_cm": 8.0,  # 이미지 없을 때 빈 칸 높이
        "priority":    2,
        "category":    "bm_model",
        "hint":        (
            "수익구조(구독요금/화이트라벨/커미션)를 원형 또는 블록 다이어그램으로 표현.\n"
            "고객군(중소기업/컨설팅기관) → 서비스 → 수익 흐름을 1장에 압축 권장."
        ),
    },
    # ─ SLOT 3 : 데이터 상품 및 활용 서비스 필요성 직후 ──────────
    # 기술 아키텍처 / 데이터 파이프라인
    {
        "slot_id":     "SLOT_TECH_ARCH",
        "location":    "after_paragraph",
        "para_keyword":"나. 데이터 상품 및 활용 서비스 필요성",
        "insert_offset": 2,
        "blank_height_cm": 8.0,
        "priority":    2,
        "category":    "tech_stack",
        "hint":        (
            "데이터 수집(크롤러·API) → 정형화(NLP·분류) → 매칭(AI 엔진) → "
            "알림(앱/이메일) 레이어를 4단 블록으로 도식화.\n"
            "사용 기술 스택(Python, FastAPI, AWS 등)을 각 블록에 표기하면 신뢰도 상승."
        ),
    },
    # ─ SLOT 4 : 기대효과 직후 ────────────────────────────────────
    # KPI 목표 인포그래픽
    {
        "slot_id":     "SLOT_EXPECTED_KPI",
        "location":    "after_paragraph",
        "para_keyword":"가. 기대효과",
        "insert_offset": 2,
        "blank_height_cm": 7.0,
        "priority":    2,
        "category":    "market_data",
        "hint":        (
            "단기/중기/장기 KPI 목표(파일럿 30개사 → 200개사 → 전국 커버리지)를 "
            "타임라인 또는 증가 막대 그래프로 표현.\n"
            "정보 수집 시간 '주 8h → 30min' 절감 효과를 Before/After 비교로 강조."
        ),
    },
    # ─ SLOT 5 : 시장현황 인포그래픽 (선택) ──────────────────────
    {
        "slot_id":     "SLOT_MARKET_CHART",
        "location":    "after_paragraph",
        "para_keyword":"1. 사업(과제) 개요",
        "insert_offset": 1,
        "priority":    3,       # 선택 (기본 미삽입)
        "category":    "market_data",
        "hint":        (
            "국내 중소기업 수출지원 시장 2.3조 원 / GovTech 성장률 18%를 "
            "파이차트 또는 성장 꺾은선 그래프로 표현."
        ),
    },
]


# ════════════════════════════════════════════════════════════════
# 추천 텍스트 생성 함수
# ════════════════════════════════════════════════════════════════

def _make_caption(slot: dict, content: dict) -> str:
    """
    슬롯과 content를 기반으로 구체적인 이미지 추천 설명문을 생성.
    실제 사업 내용(project_title, service명 등)을 텍스트에 반영.
    """
    meta      = content.get("meta", {})
    company   = content.get("company", {})
    narrative = content.get("narrative", {})

    project_title  = meta.get("project_title", "본 사업")
    # service_name: meta > company.industry > bm_intro 첫 줄에서 추출
    service_name = (
        meta.get("service_name")
        or meta.get("service", "")
        or company.get("service_name", "")
        or company.get("product_name", "")
        or ""
    )
    if not service_name:
        bm = narrative.get("bm_intro", "")
        # "MarketGate AI" 같은 제품명 추출 시도 (영문+한글 혼합 패턴)
        m = re.match(r'^([A-Za-z][A-Za-z0-9\s]*(?:AI|Pro|Plus|Gate|Hub)?)\s', bm)
        if m:
            service_name = m.group(1).strip()
        else:
            service_name = company.get("industry", "서비스") or "서비스"
    industry       = company.get("industry", "해당 분야")
    differentiator = narrative.get("differentiator", "")

    # 차별화 요소 첫 번째 항목 추출
    diff_first = ""
    if differentiator:
        lines = [l.strip() for l in differentiator.split("\n") if l.strip()]
        if lines:
            diff_first = re.sub(r'^[①②③·\-\d\.]\s*', '', lines[0])[:60]

    sid = slot["slot_id"]

    if sid == "SLOT_OVERVIEW_IMG":
        return (
            f"【이미지 추천】 {service_name} 서비스 전체 구조도\n"
            f"· 표현 내용: 데이터 수집 → AI 분류·매칭 → 기업 알림 전달 흐름\n"
            f"· 강조 포인트: {diff_first or '핵심 차별화 기능'}\n"
            f"· 권장 형식: 좌→우 플로우 차트 / 크기 A4 가로(14×9cm)\n"
            f"· 제작 도구: Figma, Canva, draw.io, PowerPoint SmartArt\n"
            f"▷ 이미지 파일 경로를 project_input.json의 assets[0].path에 입력하세요."
        )
    elif sid == "SLOT_BM_FLOW":
        return (
            f"【이미지 추천】 {service_name} 비즈니스 모델(BM) 다이어그램\n"
            f"· 표현 내용: 고객군(중소기업·컨설팅기관) → 서비스 채널 → 수익구조\n"
            f"· 핵심 요소: 구독요금(월 19,900원~49,900원), 화이트라벨(월 300,000원)\n"
            f"· 권장 형식: Business Model Canvas 요약 또는 수익 흐름도\n"
            f"· 제작 도구: Canva BM Canvas 템플릿, Miro, draw.io\n"
            f"▷ 이미지 파일 경로를 project_input.json의 assets[1].path에 입력하세요."
        )
    elif sid == "SLOT_TECH_ARCH":
        return (
            f"【이미지 추천】 {service_name} 데이터 파이프라인·기술 아키텍처\n"
            f"· 레이어 구성: ① 데이터 수집(크롤러·API) ② 정형화(NLP) "
            f"③ AI 매칭 엔진 ④ 기업 알림\n"
            f"· 표기 기술: Python, FastAPI, AWS/GCP, 추천 모델(HS Code 분류)\n"
            f"· 권장 형식: 4단 수직 블록 또는 계층형 아키텍처 다이어그램\n"
            f"· 제작 도구: draw.io, Lucidchart, AWS Architecture Diagram\n"
            f"▷ 이미지 파일 경로를 project_input.json의 assets에 추가하세요."
        )
    elif sid == "SLOT_EXPECTED_KPI":
        return (
            f"【이미지 추천】 {project_title} 기대효과 KPI 인포그래픽\n"
            f"· 핵심 수치: 정보수집 8h→30min 단축 / 파일럿 30개사 → 200개사 확장\n"
            f"· 표현 형식: ① Before/After 비교 ② 단계별 성장 막대 그래프\n"
            f"· 강조 색상: 개선 수치(파란계열), 목표값(주황·강조)\n"
            f"· 제작 도구: Canva 인포그래픽 템플릿, Excel 차트, Tableau Public\n"
            f"▷ 이미지 파일 경로를 project_input.json의 assets에 추가하세요."
        )
    elif sid == "SLOT_MARKET_CHART":
        return (
            f"【이미지 추천】 {industry} 시장 규모·성장성 차트\n"
            f"· 핵심 수치: 연간 2.3조 원 시장 / GovTech 연평균 18% 성장\n"
            f"· 표현 형식: 파이차트(시장 구성) + 꺾은선(연도별 성장률)\n"
            f"· 출처 표기: 산업부·중기부 발표 자료 반드시 표기\n"
            f"· 제작 도구: Excel, Google Sheets 차트 → PNG 내보내기\n"
            f"▷ 이미지 파일 경로를 project_input.json의 assets에 추가하세요."
        )
    else:
        return f"【이미지 추천】 {service_name} 관련 이미지 삽입 위치"


def _make_title(slot: dict, content: dict) -> str:
    """슬롯별 이미지 제목 생성."""
    # _make_caption과 동일한 service_name 추출 로직 사용
    fake_content = {"meta": content.get("meta", {}),
                    "company": content.get("company", {}),
                    "narrative": content.get("narrative", {})}
    # service_name 재계산 (동일 로직)
    meta = fake_content["meta"]
    company = fake_content["company"]
    narrative = fake_content["narrative"]
    service_name = (
        meta.get("service_name") or meta.get("service", "")
        or company.get("service_name", "") or company.get("product_name", "") or ""
    )
    if not service_name:
        bm = narrative.get("bm_intro", "")
        m = re.match(r'^([A-Za-z][A-Za-z0-9\s]*(?:AI|Pro|Plus|Gate|Hub)?)\s', bm)
        service_name = m.group(1).strip() if m else (company.get("industry", "서비스") or "서비스")

    sid = slot["slot_id"]
    titles = {
        "SLOT_OVERVIEW_IMG":   "< 그림 1. MarketGate AI 서비스 운영 흐름도 >",
        "SLOT_BM_FLOW":        f"< 그림 2. {service_name} 비즈니스 모델 다이어그램 >",
        "SLOT_TECH_ARCH":      "< 그림 2. 공고 정형화 및 AI 매칭 기술 아키텍처 >",
        "SLOT_EXPECTED_KPI":   "< 그림 3. KPI 목표 및 기대효과 로드맵 >",
        "SLOT_MARKET_CHART":   "< 그림 4. 시장 규모 및 성장성 차트 >",
    }
    return titles.get(sid, "< 이미지 제목 >")


# ════════════════════════════════════════════════════════════════
# ImageAdvisor 클래스
# ════════════════════════════════════════════════════════════════

class ImageAdvisor:
    """
    섹션 내용 기반 이미지 추천 에이전트.

    run(content) → content
      content["image_recommendations"] 키에 추천 슬롯 목록 추가.
      content["image_placeholders"]    키에 DOCX 삽입용 텍스트 블록 추가.
    """

    def __init__(self, insert_threshold: int = 2):
        """
        Args:
            insert_threshold: 이 우선순위 이하 슬롯만 placeholder 생성
                              1=필수만, 2=필수+권장(기본), 3=전체
        """
        self.insert_threshold = insert_threshold
        self._slots_generated: list[str] = []

    # ── 메인 실행 ──────────────────────────────────────────────
    def run(self, content: dict) -> dict:
        """
        content를 분석하여 image_slots / image_placeholders / blank_image_slots를 생성.

        ┌── 이미지 파일 존재 여부 분기 ──────────────────────────────────────────
        │  파일 존재   → image_slots (write_docx STEP 1-C 에서 실제 이미지 삽입)
        │  파일 없음   → image_placeholders (텍스트 안내 삽입)
        │             + blank_image_slots (빈 칸 표 삽입)
        └────────────────────────────────────────────────────────────────────────
        assets 배열 순서와 _SLOT_TEMPLATES 순서를 1:1 매칭.
        assets[0] → SLOT_OVERVIEW_IMG, assets[1] → SLOT_BM_FLOW, …
        """
        import os as _os

        recommendations = []
        image_slots     = {}   # slot_id → {image_path, location, ...}  ← 실제 삽입
        placeholders    = {}   # slot_id → {title, caption_text}         ← 텍스트 안내
        blank_slots     = []   # 이미지 없을 때 빈 칸 배정 목록

        # ── assets 배열에서 슬롯별 이미지 경로 추출 ──────────────────
        # 우선순위:
        #   1) slot_id 명시 자산을 직접 매핑
        #   2) slot_id 없는 자산만 기존 순서 기반 fallback 적용
        assets = content.get("assets", [])
        slot_asset_map: dict[str, str] = {}
        ordered_assets = []
        for asset in assets:
            path = asset.get("path", "")
            slot_id = asset.get("slot_id", "")
            if slot_id and path and _os.path.exists(path):
                slot_asset_map[slot_id] = path
            else:
                ordered_assets.append(asset)

        active_idx = 0   # threshold 이하 슬롯 카운터
        for slot in _SLOT_TEMPLATES:
            if slot["priority"] <= self.insert_threshold:
                if slot["slot_id"] not in slot_asset_map and active_idx < len(ordered_assets):
                    path = ordered_assets[active_idx].get("path", "")
                    if path and _os.path.exists(path):
                        slot_asset_map[slot["slot_id"]] = path
                active_idx += 1

        for slot in _SLOT_TEMPLATES:
            slot_id  = slot["slot_id"]
            priority = slot["priority"]

            caption = _make_caption(slot, content)
            title   = _make_title(slot, content)
            rec     = {**slot, "title": title, "caption_text": caption}
            recommendations.append(rec)

            if priority > self.insert_threshold:
                continue   # 선택 슬롯: 삽입 안 함

            self._slots_generated.append(slot_id)
            has_image = slot_id in slot_asset_map

            if has_image:
                # ── 실제 이미지 삽입 슬롯 ────────────────────────────
                image_slots[slot_id] = {
                    "location":     slot["location"],
                    "image_path":   slot_asset_map[slot_id],
                    "table_index":  slot.get("table_index"),
                    "row":          slot.get("row"),
                    "cell":         slot.get("cell"),
                    "para_keyword": slot.get("para_keyword", ""),
                    "insert_offset":slot.get("insert_offset", 1),
                    "width_cm":     slot.get("width_cm", 12.0),
                    "caption":      title.strip("<> "),
                }
                print(f"  [IMAGE_ADVISOR] ✅ 이미지 슬롯: {slot_id} → {slot_asset_map[slot_id]}")
            else:
                # ── 텍스트 placeholder 삽입 슬롯 ─────────────────────
                placeholders[slot_id] = {
                    "title":        title,
                    "caption_text": caption,
                    "priority":     priority,
                    "location":     slot["location"],
                    "para_keyword": slot.get("para_keyword", ""),
                    "table_index":  slot.get("table_index"),
                    "row":          slot.get("row"),
                    "cell":         slot.get("cell"),
                    "row2":         slot.get("row2"),
                    "cell2":        slot.get("cell2"),
                    "insert_offset":slot.get("insert_offset", 2),
                }
                # after_paragraph 위치: 빈 칸 표도 배정
                if slot["location"] == "after_paragraph":
                    blank_slots.append({
                        "slot_id":       slot_id,
                        "para_keyword":  slot.get("para_keyword", ""),
                        "label":         f"[ 📸 {title.strip('<> ')} ]",
                        "height_cm":     slot.get("blank_height_cm", 8.0),
                        "insert_offset": slot.get("insert_offset", 2)
                                         + len(caption.split("\n")) + 2,
                    })

        content["image_recommendations"] = recommendations
        content["image_slots"]           = image_slots      # ← NEW
        content["image_placeholders"]    = placeholders
        content["blank_image_slots"]     = blank_slots
        return content

    # ── 상태 요약 ──────────────────────────────────────────────
    def summary(self) -> str:
        total = len(_SLOT_TEMPLATES)
        gen   = len(self._slots_generated)
        return (f"slots_total={total}, "
                f"placeholders_generated={gen}{self._slots_generated}")

    # ── 추천 리포트 출력 ───────────────────────────────────────
    def print_report(self, content: dict) -> None:
        """콘솔에 이미지 추천 리포트 출력 (디버깅·QA용)."""
        recs = content.get("image_recommendations", [])
        print("\n" + "═" * 60)
        print("  📸 이미지 추천 리포트")
        print("═" * 60)
        priority_label = {1: "🔴 필수", 2: "🟡 권장", 3: "⚪ 선택"}
        for r in recs:
            pri = priority_label.get(r["priority"], "?")
            loc = r["location"]
            if loc == "table_cell":
                pos = f"표#{r['table_index']} [{r['row']},{r['cell']}]"
            else:
                kw = r.get("para_keyword", "")
                pos = f"'{kw}' 단락 이후"
            print(f"\n  {pri}  [{r['slot_id']}]")
            print(f"  위치: {pos}")
            print(f"  제목: {r['title']}")
            print(f"  카테고리: {r['category']}")
            # caption 첫 줄만 출력
            first_line = r["caption_text"].split("\n")[0]
            print(f"  추천: {first_line}")
            print(f"  힌트: {r['hint'].split(chr(10))[0]}")
        print("\n" + "═" * 60)
