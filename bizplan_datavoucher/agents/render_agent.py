"""
agents/render_agent.py
-----------------------
DOCX 실제 삽입 에이전트 — BizPlanInjector 호출 총괄

담당 역할:
  - content 딕셔너리를 BizPlanInjector가 사용하는 injector_content 구조로 변환
  - BizPlanInjector.run() 호출 (파란 안내문구 제거 + 표/섹션 주입)
  - 이미지 삽입 (inject_image)
  - 최종 DOCX 저장

이 에이전트는 단 하나의 원칙을 지킵니다:
  "렌더링은 마지막 한 곳에서만."
  Writer / Table / Asset 에이전트가 내용을 만들고,
  Render 에이전트만 DOCX에 손을 댑니다.

테이블 인덱스 매핑 (datavoucher_2026.docx 기준):
  실제 템플릿 확보 후 아래 TABLE_INDEX 딕셔너리를 조정하세요.
  템플릿 변경 시 이 파일만 수정하면 됩니다.
"""

from __future__ import annotations
import os
import sys

# BizPlanInjector가 같은 프로젝트 내에 있는 경우 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from bizplan_injector.core.injector import BizPlanInjector
    INJECTOR_AVAILABLE = True
except ImportError:
    INJECTOR_AVAILABLE = False


# ── 테이블 인덱스 매핑 (템플릿 확보 후 조정) ─────────────────────
# 키: 논리적 표 이름  /  값: DOCX 내 실제 표 인덱스 (0부터 시작)
TABLE_INDEX = {
    "budget":    0,   # 사업비 편성 비중표
    "schedule":  1,   # 추진일정표
    "team":      2,   # 수행인력 현황표
    "hire_plan": 3,   # 추가 인력 고용계획표
}

# ── 섹션 키워드 매핑 ─────────────────────────────────────────────
SECTION_KEYWORD = {
    "problem":         "목적 및 필요성",
    "solution":        "실현방안",
    "market_status":   "시장현황",
    "bm_intro":        "비즈니스 모델",
    "differentiator":  "특장점",
    "expected_effect": "기대효과",
}


class RenderAgent:
    """
    DOCX 렌더링 에이전트.

    run(content, template_path, output_path) → stats dict
    """

    def __init__(self):
        self._stats: dict = {}

    # ── 메인 실행 ──────────────────────────────────────────────
    def run(self, content: dict, template_path: str, output_path: str) -> dict:
        """
        content를 BizPlanInjector로 DOCX에 삽입하고 저장.

        Args:
            content:       통합 content (WriterAgent / TableAgent / AssetAgent 처리 완료)
            template_path: 원본 DOCX 양식 경로
            output_path:   출력 DOCX 파일 경로

        Returns:
            BizPlanInjector.run() 반환 stats + 추가 정보
        """
        if not INJECTOR_AVAILABLE:
            return self._dry_run(content, template_path, output_path)

        if not os.path.exists(template_path):
            raise FileNotFoundError(
                f"템플릿 파일을 찾을 수 없습니다: {template_path}\n"
                "templates/ 폴더에 datavoucher_2026.docx를 넣어주세요."
            )

        # ── injector_content 구성 ───────────────────────────────
        injector_content = self._build_injector_content(content)

        # ── BizPlanInjector 실행 ────────────────────────────────
        inj = BizPlanInjector(template_path)
        inj.set_content(injector_content)
        stats = inj.run()

        # ── 이미지 삽입 (run() 이후) ────────────────────────────
        for img in content.get("images", []):
            success = inj.inject_image(
                keyword    = img["keyword"],
                image_path = img["image_path"],
                width_cm   = img.get("width_cm", 14.0),
                height_cm  = img.get("height_cm", 9.0),
                align      = img.get("align", "center"),
            )
            stats["images_injected"] = stats.get("images_injected", 0) + (1 if success else 0)

        inj.save(output_path)
        self._stats = stats
        return stats

    # ── injector_content 변환 ────────────────────────────────
    def _build_injector_content(self, content: dict) -> dict:
        """
        통합 content → BizPlanInjector content.json 포맷으로 변환.

        BizPlanInjector가 기대하는 구조:
          {
            "table_cells": [...],
            "table_rows":  [...],
            "sections":    [...],
            "images":      [...],
            "delete_tables": [...]
          }
        """
        ic: dict = {
            "delete_tables": [],
            "table_cells":   [],
            "table_rows":    [],
            "sections":      [],
            "images":        [],
        }

        company = content.get("company", {})
        ceo     = content.get("ceo", {})
        meta    = content.get("meta", {})
        tables  = content.get("_tables", {})

        # ── 기업 기본정보 셀 주입 ───────────────────────────────
        # 실제 표 인덱스/행/열은 템플릿 확보 후 아래를 수정하세요
        overview_cells = [
            # (table_idx, row_idx, cell_idx, value)
            (0, 1, 1, company.get("name", "")),
            (0, 1, 3, meta.get("project_title", "")),
            (0, 2, 1, ceo.get("name", "")),
            (0, 2, 3, company.get("founded", "")),
            (0, 3, 1, company.get("address", "")),
            (0, 3, 3, str(company.get("employee_count", ""))),
            (0, 4, 1, meta.get("data_use_purpose", "")),
            (0, 5, 1, meta.get("goal_100char", "")),
        ]
        for t, r, c, val in overview_cells:
            ic["table_cells"].append({
                "table": t, "row": r, "cell": c,
                "text": val, "size": 18, "align": "left"
            })

        # ── 사업비 편성 비중표 ──────────────────────────────────
        if tables.get("budget_rows"):
            ic["table_rows"].append({
                "table": TABLE_INDEX["budget"],
                "rows":  tables["budget_rows"],
                "header_rows": 1,
                "size": 18
            })

        # ── 추진일정표 ──────────────────────────────────────────
        if tables.get("schedule_rows"):
            ic["table_rows"].append({
                "table": TABLE_INDEX["schedule"],
                "rows":  tables["schedule_rows"],
                "header_rows": 1,
                "size": 18
            })

        # ── 수행인력 현황표 ─────────────────────────────────────
        if tables.get("team_rows"):
            ic["table_rows"].append({
                "table": TABLE_INDEX["team"],
                "rows":  tables["team_rows"],
                "header_rows": 1,
                "size": 18
            })

        # ── 추가 인력 고용계획표 ────────────────────────────────
        if tables.get("hire_rows"):
            ic["table_rows"].append({
                "table": TABLE_INDEX["hire_plan"],
                "rows":  tables["hire_rows"],
                "header_rows": 1,
                "size": 18
            })

        # ── 서술형 섹션 주입 ────────────────────────────────────
        narrative = content.get("narrative", {})
        for field, keyword in SECTION_KEYWORD.items():
            text = narrative.get(field, "")
            if text.strip():
                lines = [l for l in text.split("\n") if l.strip()]
                ic["sections"].append({
                    "keyword": keyword,
                    "lines":   lines,
                    "size":    18
                })

        # ── 이미지 ──────────────────────────────────────────────
        # (inject_image는 run() 이후 별도 호출하므로 여기서는 비워둠)

        return ic

    # ── 드라이런 (BizPlanInjector 없을 때) ──────────────────────
    def _dry_run(self, content: dict, template_path: str, output_path: str) -> dict:
        """
        BizPlanInjector가 설치되지 않은 환경에서의 드라이런.
        실제 DOCX 생성 없이 content 구조만 검증 후 JSON으로 저장.
        """
        import json
        dry_path = output_path.replace(".docx", "_DRY_RUN.json")
        with open(dry_path, "w", encoding="utf-8") as f:
            # 직렬화할 수 없는 키 제거
            safe = {k: v for k, v in content.items() if not k.startswith("_")}
            json.dump(safe, f, ensure_ascii=False, indent=2)
        print(f"  [DRY RUN] BizPlanInjector 미설치. 내용 검증 파일 저장: {dry_path}")
        return {"dry_run": True, "output": dry_path}

    # ── 상태 요약 ──────────────────────────────────────────────
    def summary(self) -> str:
        return str(self._stats)
