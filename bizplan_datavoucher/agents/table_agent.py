"""
agents/table_agent.py
----------------------
표 데이터 구조화 에이전트

담당 영역:
  - 사업비 편성 비중표  (budget_mix)
  - 추진일정표          (schedule)
  - 수행인력 현황표     (team)
  - 추가 인력 고용계획표 (team 중 is_new_hire=True)

역할:
  1. 원본 값 검증  (합계 100%, 참여율 범위 등)
  2. 렌더링용 구조로 변환  (BizPlanInjector의 table_cells / table_rows 포맷)
  3. 경고/오류 플래그 수집  (QAAgent가 참조)

이 에이전트는 논리를 새로 만들지 않습니다.
배정된 수치를 정리·검증·구조화하는 것만 담당합니다.
"""

from __future__ import annotations
from typing import Any


# ── 사업비 항목 한글 라벨 ─────────────────────────────────────
BUDGET_LABELS = {
    "planning":   "기획",
    "purchase":   "구매",
    "collection": "수집",
    "processing": "가공",
    "analysis":   "분석",
}

# 추진일정 월 컬럼 수 (데이터바우처: 6개월 과제)
SCHEDULE_MONTHS = 6


class TableAgent:
    """
    표 데이터 구조화 에이전트.

    run(content) → content  (table_cells / table_rows 키 추가)
    """

    def __init__(self):
        self._warnings: list[str] = []
        self._errors:   list[str] = []
        self._processed: list[str] = []

    # ── 메인 실행 ──────────────────────────────────────────────
    def run(self, content: dict) -> dict:
        """
        content의 budget_mix / schedule / team을
        BizPlanInjector가 바로 사용할 수 있는 구조로 변환.

        content에 다음 키를 추가합니다:
          - content["_tables"]["budget_rows"]   : 사업비 렌더링 데이터
          - content["_tables"]["schedule_rows"] : 일정표 렌더링 데이터
          - content["_tables"]["team_rows"]     : 인력표 렌더링 데이터
          - content["_tables"]["hire_rows"]     : 고용계획표 렌더링 데이터
          - content["_table_warnings"]          : 경고 목록 (QA용)
          - content["_table_errors"]            : 오류 목록 (QA용)
        """
        tables = {}

        tables["budget_rows"]   = self._build_budget(content.get("budget_mix", {}),
                                                       content.get("budget_total", 0))
        tables["schedule_rows"] = self._build_schedule(content.get("schedule", []))
        tables["team_rows"]     = self._build_team(content.get("team", []))
        tables["hire_rows"]     = self._build_hire_plan(content.get("team", []))

        content["_tables"]         = tables
        content["_table_warnings"] = self._warnings
        content["_table_errors"]   = self._errors
        return content

    # ── 사업비 편성 비중표 ────────────────────────────────────
    def _build_budget(self, budget_mix: dict, total: int) -> list[dict]:
        """
        budget_mix를 표 행 목록으로 변환.

        반환 포맷:
          [{"cells": ["항목", "비중(%)", "금액(원)"], "aligns": [...]}, ...]
        """
        rows = []
        total_pct = 0

        for key, label in BUDGET_LABELS.items():
            pct = budget_mix.get(key, 0)
            total_pct += pct
            amount = int(total * pct / 100) if total else 0
            rows.append({
                "cells": [label, f"{pct}%", f"{amount:,}원"],
                "aligns": ["center", "center", "right"]
            })

        # 합계 행
        rows.append({
            "cells": ["합계", f"{total_pct}%", f"{total:,}원"],
            "aligns": ["center", "center", "right"]
        })

        # 검증
        if total_pct != 100:
            self._errors.append(f"사업비 비중 합계가 {total_pct}% 입니다 (100% 필요)")

        purchase    = budget_mix.get("purchase", 0)
        processing  = budget_mix.get("processing", 0)
        if purchase == 0 and processing == 0:
            self._errors.append("구매 또는 가공 중 최소 1개 항목 > 0% 필수 (데이터바우처 요건)")

        max_single = max(budget_mix.values(), default=0)
        if max_single > 70:
            self._warnings.append(
                f"단일 항목 비중이 {max_single}%로 과도합니다 (70% 초과 시 미선정 위험)"
            )

        self._processed.append("budget")
        return rows

    # ── 추진일정표 ────────────────────────────────────────────
    def _build_schedule(self, schedule: list) -> list[dict]:
        """
        schedule 목록을 Gantt 스타일 표 행으로 변환.

        반환 포맷:
          [{"cells": ["업무명", "M1", "M2", ..., "M6", "비중"], "aligns": [...]}, ...]
        """
        rows = []
        total_weight = 0

        for item in schedule:
            task   = item.get("task", "")
            weight = item.get("weight", 0)
            total_weight += weight

            month_cells = []
            for m in range(1, SCHEDULE_MONTHS + 1):
                flag = item.get(f"m{m}", False)
                month_cells.append("●" if flag else "")

            rows.append({
                "cells": [task] + month_cells + [f"{weight}%"],
                "aligns": ["left"] + ["center"] * SCHEDULE_MONTHS + ["center"]
            })

        # 합계 행
        rows.append({
            "cells": ["합계"] + [""] * SCHEDULE_MONTHS + [f"{total_weight}%"],
            "aligns": ["center"] + ["center"] * SCHEDULE_MONTHS + ["center"]
        })

        if total_weight != 100:
            self._warnings.append(
                f"추진일정 비중 합계가 {total_weight}%입니다 (100% 권장)"
            )

        self._processed.append("schedule")
        return rows

    # ── 수행인력 현황표 ───────────────────────────────────────
    def _build_team(self, team: list) -> list[dict]:
        """
        team 목록을 수행인력 현황 표 행으로 변환.
        신규 채용 인력도 포함 (기존 재직 + 신규 채용 모두 표시).

        반환 포맷:
          [{"cells": ["성명", "역할", "참여율(%)"], "aligns": [...]}, ...]
        """
        rows = []
        for member in team:
            name          = member.get("name", "")
            role          = member.get("role", "")
            participation = member.get("participation", 0)
            is_new        = member.get("is_new_hire", False)
            note          = " (신규채용 예정)" if is_new else ""

            rows.append({
                "cells": [name, f"{role}{note}", f"{participation}%"],
                "aligns": ["center", "left", "center"]
            })

            # 참여율 검증
            if not (10 <= participation <= 100):
                self._warnings.append(
                    f"수행인력 '{name}'의 참여율({participation}%)이 권고 범위(10~100%)를 벗어납니다"
                )

        self._processed.append("team")
        return rows

    # ── 추가 인력 고용계획표 ──────────────────────────────────
    def _build_hire_plan(self, team: list) -> list[dict]:
        """
        is_new_hire=True 인 인력만 추려 고용계획 표 행으로 변환.

        반환 포맷:
          [{"cells": ["성명", "역할/담당", "채용 예정 시기"], "aligns": [...]}, ...]
        """
        rows = []
        for member in team:
            if not member.get("is_new_hire", False):
                continue
            rows.append({
                "cells": [
                    member.get("name", ""),
                    member.get("role", ""),
                    "과제 착수 후 1개월 내"   # 기본값; project_input에서 hire_timing 필드 추가 가능
                ],
                "aligns": ["center", "left", "center"]
            })

        if not rows:
            rows.append({
                "cells": ["해당없음", "", ""],
                "aligns": ["center", "left", "center"]
            })

        self._processed.append("hire_plan")
        return rows

    # ── 상태 요약 ──────────────────────────────────────────────
    def summary(self) -> str:
        return (f"processed={self._processed}, "
                f"warnings={len(self._warnings)}, errors={len(self._errors)}")
