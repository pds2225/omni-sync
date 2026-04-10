"""
render_agent.py — DOCX 렌더링 총괄 에이전트
=============================================
역할: content dict → injector_content 변환 후 docx_writer.write_docx() 호출.
      이미지 슬롯 결정, formatter 적용까지 담당.

주요 상수:
    TABLE_INDEX     : 작성요령 삭제 후 표 인덱스 (overview=3, budget=5, schedule=7 ...)
    SECTION_KEYWORD : {narrative_key: "단락 헤딩 텍스트"} 매핑
                      새 섹션 추가 시 이 dict에 등록

주요 메서드:
    RenderAgent.run(content, template_path, output_path) -> stats
    RenderAgent._direct_write(...)   ← BizPlanInjector 없을 때 사용 (현재 경로)
    RenderAgent._build_injector_content(content) -> injector_content
    RenderAgent._build_image_placeholders(content) -> image_placeholders
        ★ image_slots에 등록된 슬롯은 placeholders에서 자동 제외 (중복 방지)

injector_content 키 목록:
    cells, sections, image_slots, image_placeholders,
    blank_image_slots, trim_tables
"""
import os

# ── BizPlanInjector 가용 여부 ─────────────────────────────────────
INJECTOR_AVAILABLE = False
try:
    from bizplan_injector.core.injector import BizPlanInjector
    INJECTOR_AVAILABLE = True
except ImportError:
    pass

# ── python-docx 직접 작성기 (BizPlanInjector 없을 때 사용) ──────
DOCX_WRITER_AVAILABLE = False
try:
    from agents.docx_writer import write_docx
    DOCX_WRITER_AVAILABLE = True
except ImportError:
    try:
        from docx_writer import write_docx
        DOCX_WRITER_AVAILABLE = True
    except ImportError:
        pass

# ── ImageAdvisor (이미지 추천 텍스트 생성) ────────────────────────
IMAGE_ADVISOR_AVAILABLE = False
try:
    from agents.image_advisor import ImageAdvisor
    IMAGE_ADVISOR_AVAILABLE = True
except ImportError:
    try:
        from image_advisor import ImageAdvisor
        IMAGE_ADVISOR_AVAILABLE = True
    except ImportError:
        pass

# ── Formatter (타이틀 볼드 / 중요 텍스트 강조) ─────────────────────
FORMATTER_AVAILABLE = False
try:
    from agents.formatter import apply_formatting
    FORMATTER_AVAILABLE = True
except ImportError:
    try:
        from formatter import apply_formatting
        FORMATTER_AVAILABLE = True
    except ImportError:
        pass

# ── 표 인덱스 (template_parser.py 분석 결과 확정) ────────────────
TABLE_INDEX = {
    "overview":   4,   # 수요기업 개요 (과제명/목표/핵심역량/시장현황/필요성)
    "budget":    13,   # 사업비 편성 비중
    "schedule":  22,   # 추진 일정 간트
    "staff_cnt": 27,   # 재직/고용 인원 수 요약
    "team":      29,   # 참여인력 현황
    "hire_plan": 30,   # 추가 인력 고용계획
}

# ── 섹션 키워드 (단락 헤딩 → inject_after_keyword) ───────────────
# 키: content 필드명  값: DOCX 내 단락 텍스트 (정확히 일치해야 함)
SECTION_KEYWORD = {
    # ── 1. 사업(과제) 개요 ─────────────────────────────
    "problem":         "가. 사업(과제) 목적 및 필요성",
    "bm_intro":        "나. 비즈니스 모델 소개",
    "differentiator":  "다. 비즈니스 모델의 특장점",
    # ── 2. 세부 추진계획 및 방법 ────────────────────────
    "goal_100char":    "가. 데이터를 활용한 사업(창업)목표",
    "solution":        "나. 데이터 상품 및 활용 서비스 필요성",
    # ── 3. 활성화 방안 ──────────────────────────────────
    "alliance_plan":   "가. 대외 제휴 계획",
    "pr_plan":         "나. 홍보계획(예비창업자의 경우 자금소요 및 조달 계획 작성)",
    # ── 4. 기대효과 및 향후계획 ─────────────────────────
    "expected_effect": "가. 기대효과",
    "future_plan":     "나. 향후계획",
    # ── 5. 산출물 공개·활용 계획 ────────────────────────
    "output_plan":     "가. 산출물 공개·활용 방안",
    "output_effect":   "나. 산출물 공개·활용 효과",
    # ── 수행인력 ────────────────────────────────────────
    "ceo_career":      "가. 대표자 역량",
    # ── 2. 세부 추진계획 신규 보완 항목 ─────────────────────
    "budget_rationale": "다. 사업비 편성 비중",
    "privacy_note":    "라. 개인정보 관리방안(※해당 수요기업에 한하여 작성)",
}

# ── 열 매핑 ──────────────────────────────────────────────────────
BUDGET_COL = {           # 표 #13, row 2
    "planning":   1,
    "purchase":   2,
    "collection": 3,
    "processing": 4,
    "analysis":   5,
    "total":      6,
}
SCHEDULE_MONTH_COL = {   # 표 #22, row 2~19
    "m1": 2, "m2": 3, "m3": 4,
    "m4": 5, "m5": 6, "m6": 7,
}
SCHEDULE_DATA_ROW_START = 2   # row 0=헤더1, row 1=헤더2(M/M+1…), row 2~=데이터


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
            stats dict  (dry_run=True 이면 JSON만 생성)
        """
        if not INJECTOR_AVAILABLE:
            # python-docx 직접 작성기 사용
            if DOCX_WRITER_AVAILABLE and os.path.exists(template_path):
                return self._direct_write(content, template_path, output_path)
            return self._dry_run(content, template_path, output_path)

        if not os.path.exists(template_path):
            raise FileNotFoundError(
                f"템플릿 파일을 찾을 수 없습니다: {template_path}\n"
                "templates/ 폴더에 datavoucher_2026.docx를 넣어주세요."
            )

        injector_content = self._build_injector_content(content)

        inj = BizPlanInjector(template_path)
        inj.set_content(injector_content)
        stats = inj.run()

        # ── 이미지 삽입 ─────────────────────────────────────────
        for img in content.get("images", []):
            if not img.get("path") or not os.path.exists(img["path"]):
                continue
            try:
                success = inj.inject_image(
                    keyword=img.get("keyword", "관련 이미지"),
                    image_path=img["path"],
                    title=img.get("title", ""),
                )
                stats["images_injected"] = stats.get("images_injected", 0) + (1 if success else 0)
            except Exception as e:
                stats.setdefault("image_errors", []).append(str(e))

        inj.save(output_path)
        self._stats = stats
        content["_render_stats"] = stats
        return stats

    # ── injector_content 변환 ─────────────────────────────────
    def _build_injector_content(self, content: dict) -> dict:
        """
        content 딕셔너리를 BizPlanInjector가 받는 injector_content 구조로 변환.

        BizPlanInjector.set_content() 스펙:
          {
            "cells":    [ {"table": int, "row": int, "cell": int, "text": str}, ... ],
            "sections": [ {"keyword": str, "text": str}, ... ],
          }
        """
        cells    = []
        sections = []
        paragraph_tables = []

        meta    = content.get("meta", {})
        company = content.get("company", {})
        ceo     = content.get("ceo", {})
        tables  = content.get("_tables", {})

        # ── 표 #4 : 수요기업 개요 ─────────────────────────────
        # [1,2] 과제명
        cells.append({"table": TABLE_INDEX["overview"], "row": 1, "cell": 2,
                       "text": meta.get("project_title", "")})
        # [2,2] 사업(과제) 개요 = 활용목적 + 100자 목표
        purpose = meta.get("data_use_purpose", "")
        goal    = meta.get("goal_100char", "")
        cells.append({"table": TABLE_INDEX["overview"], "row": 2, "cell": 2,
                       "text": f"{purpose}\n{goal}" if purpose else goal})
        # [3,2] 핵심역량
        core = "\n".join(f"· {c}" for c in content.get("core_competency", []))
        cells.append({"table": TABLE_INDEX["overview"], "row": 3, "cell": 2,
                       "text": core})
        # [4,2] 시장현황
        cells.append({"table": TABLE_INDEX["overview"], "row": 4, "cell": 2,
                       "text": content.get("narrative", {}).get("market_status", "")})
        # [5,2] 데이터 상품 및 활용서비스 필요성
        cells.append({"table": TABLE_INDEX["overview"], "row": 5, "cell": 2,
                       "text": content.get("narrative", {}).get("solution", "")})

        # [6,2~3] 관련이미지 셀 - 이미지 없으면 빈 셀로 초기화
        # (원본 안내문 ※ 삭제)
        for img_ci in [2, 3]:
            cells.append({"table": TABLE_INDEX["overview"], "row": 6, "cell": img_ci,
                           "text": " "})
            cells.append({"table": TABLE_INDEX["overview"], "row": 7, "cell": img_ci,
                           "text": " "})

        # ── 표 #13 : 사업비 편성 비중 ────────────────────────
        # row 1 체크박스: 사용 항목에 ✓, 미사용에 □
        budget_mix   = content.get("budget_mix", {})
        budget_total = content.get("budget_total", 0)
        KEY_TO_COL = {
            "planning": 1, "purchase": 2,
            "collection": 3, "processing": 4, "analysis": 5,
        }
        for key, col in KEY_TO_COL.items():
            pct = budget_mix.get(key, 0)
            cells.append({"table": TABLE_INDEX["budget"], "row": 1, "cell": col,
                           "text": "✓" if pct > 0 else "□"})
        # row 2 사업비 비중 (원/%)
        total_used = 0
        for key, col in KEY_TO_COL.items():
            pct = budget_mix.get(key, 0)
            amt = int(budget_total * pct / 100)
            total_used += amt
            cells.append({"table": TABLE_INDEX["budget"], "row": 2, "cell": col,
                           "text": f"{amt:,}원/{pct}%"})
        # 계 열
        cells.append({"table": TABLE_INDEX["budget"], "row": 2, "cell": 6,
                       "text": f"{budget_total:,}원/100%"})

        # ── 표 #22 : 추진 일정 ───────────────────────────────
        schedule = content.get("schedule", [])
        for i, task in enumerate(schedule):
            data_row = SCHEDULE_DATA_ROW_START + i
            if data_row > 19:
                break
            cells.append({"table": TABLE_INDEX["schedule"], "row": data_row, "cell": 0,
                           "text": task.get("task", "")})
            # 수행내용 (col 1) ← 추가
            cells.append({"table": TABLE_INDEX["schedule"], "row": data_row, "cell": 1,
                           "text": task.get("content", "")})
            # 월별 간트 ●
            for m_key, col in SCHEDULE_MONTH_COL.items():
                mark = "●" if task.get(m_key) else ""
                cells.append({"table": TABLE_INDEX["schedule"], "row": data_row, "cell": col,
                               "text": mark})
            # 비중
            cells.append({"table": TABLE_INDEX["schedule"], "row": data_row, "cell": 8,
                           "text": f"{task.get('weight', 0)}%"})

        # ── 표 #27 : 재직/고용 인원 수 ──────────────────────
        team         = content.get("team", [])
        existing     = [m for m in team if not m.get("is_new_hire")]
        new_hires    = [m for m in team if m.get("is_new_hire")]
        cells.append({"table": TABLE_INDEX["staff_cnt"], "row": 0, "cell": 1,
                       "text": str(len(existing))})
        cells.append({"table": TABLE_INDEX["staff_cnt"], "row": 0, "cell": 3,
                       "text": str(len(new_hires))})

        # ── 표 #29 : 참여인력 현황 ───────────────────────────
        for i, member in enumerate(team):
            data_row = 1 + i
            if data_row > 6:
                break
            cells.append({"table": TABLE_INDEX["team"], "row": data_row, "cell": 0,
                           "text": str(i + 1)})
            cells.append({"table": TABLE_INDEX["team"], "row": data_row, "cell": 1,
                           "text": member.get("title", "…")})
            cells.append({"table": TABLE_INDEX["team"], "row": data_row, "cell": 2,
                           "text": member.get("name", "")})
            cells.append({"table": TABLE_INDEX["team"], "row": data_row, "cell": 3,
                           "text": member.get("role", "")})
            cells.append({"table": TABLE_INDEX["team"], "row": data_row, "cell": 4,
                           "text": member.get("career", "")})
            cells.append({"table": TABLE_INDEX["team"], "row": data_row, "cell": 5,
                           "text": member.get("hire_date",
                                  "신규" if member.get("is_new_hire") else "")})
            cells.append({"table": TABLE_INDEX["team"], "row": data_row, "cell": 6,
                           "text": f"{member.get('participation', 0)}%"})

        # ── 표 #30 : 추가 인력 고용계획 ─────────────────────
        # project_input.json 최상위 "hire_plan" 키 우선, 없으면 _tables에서 fallback
        hire_plan = content.get("hire_plan",
                    tables.get("hire_plan_rows",
                    tables.get("hire_plan", [])))
        for i, hp in enumerate(hire_plan):
            data_row = 1 + i
            if data_row > 5:
                break
            cells.append({"table": TABLE_INDEX["hire_plan"], "row": data_row, "cell": 0,
                           "text": str(i + 1)})
            cells.append({"table": TABLE_INDEX["hire_plan"], "row": data_row, "cell": 1,
                           "text": hp.get("role", "")})
            cells.append({"table": TABLE_INDEX["hire_plan"], "row": data_row, "cell": 2,
                           "text": hp.get("skills",
                                  hp.get("required_background", ""))})
            cells.append({"table": TABLE_INDEX["hire_plan"], "row": data_row, "cell": 3,
                           "text": hp.get("hire_month",
                                  hp.get("hire_timing", ""))})

        # ── 서술 섹션 (단락 뒤 삽입) ─────────────────────────
        narrative = content.get("narrative", {})
        meta      = content.get("meta", {})
        privacy   = content.get("privacy", {})
        for field, keyword in SECTION_KEYWORD.items():
            text = ""
            if field == "ceo_career":
                career = ceo.get("career", [])
                text   = "\n".join(f"· {c}" for c in career)
            elif field == "goal_100char":
                # 데이터를 활용한 사업목표: meta에서 가져옴
                purpose = meta.get("data_use_purpose", "")
                goal    = meta.get("goal_100char", "")
                text    = f"[활용목적] {purpose}\n{goal}" if purpose else goal
            elif field == "privacy_note":
                if privacy.get("uses_personal_data", False):
                    manager = privacy.get("privacy_manager", "").strip()
                    text = (
                        f"· 개인정보 활용 예정\n· 개인정보보호관리자: {manager}"
                        if manager else
                        "· 개인정보 활용 예정\n· 개인정보보호관리자 지정 예정"
                    )
                else:
                    text = "해당없음"
            else:
                text = narrative.get(field, "")
            if text:
                sections.append({"keyword": keyword, "text": text})

        for tbl in content.get("comparison_tables", []):
            if not tbl.get("headers") or not tbl.get("rows"):
                continue
            paragraph_tables.append({
                "keyword": tbl.get("keyword", "1. 사업(과제) 개요"),
                "insert_offset": tbl.get("insert_offset", 1),
                "title": tbl.get("title", ""),
                "headers": tbl.get("headers", []),
                "rows": tbl.get("rows", []),
                "note": tbl.get("note", ""),
                "column_widths_cm": tbl.get("column_widths_cm", []),
            })

        return {"cells": cells, "sections": sections, "paragraph_tables": paragraph_tables}

    # ── ImageAdvisor 호출 ────────────────────────────────────────
    def _build_image_placeholders(self, content: dict) -> dict:
        """
        ImageAdvisor를 호출하여 이미지 추천 텍스트를 생성하고
        write_docx()가 바로 소비할 수 있는 image_placeholders 딕셔너리를 반환.

        실제 이미지가 있는 슬롯은 placeholder를 건너뜀(이미지가 이미 삽입됨).
        """
        if not IMAGE_ADVISOR_AVAILABLE:
            return {}

        # 이미 이미지가 준비된 슬롯 확인 (asset_agent 처리 결과)
        existing_images = {
            img.get("_title", "") for img in content.get("images", [])
        }

        advisor = ImageAdvisor(insert_threshold=2)  # 필수+권장만 삽입
        content = advisor.run(content)
        advisor.print_report(content)

        # write_docx용 포맷으로 변환
        # ★ image_slots에 이미 포함된 슬롯(실제 이미지 삽입 예정)은 placeholder 제외
        image_slot_ids = set(content.get("image_slots", {}).keys())

        placeholders = {}
        for rec in content.get("image_recommendations", []):
            sid      = rec["slot_id"]
            priority = rec["priority"]
            if priority > advisor.insert_threshold:
                continue  # 선택 슬롯 건너뜀
            if sid in image_slot_ids:
                continue  # 실제 이미지 삽입 슬롯 → placeholder 중복 방지

            ph = {
                "location":      rec["location"],
                "caption_text":  rec["caption_text"],
                "title":         rec["title"],
            }
            if rec["location"] == "table_cell":
                ph.update({
                    "table_index": rec.get("table_index", 3),
                    "row":         rec.get("row",  6),
                    "cell":        rec.get("cell", 2),
                    "row2":        rec.get("row2"),
                    "cell2":       rec.get("cell2"),
                })
            elif rec["location"] == "after_paragraph":
                ph.update({
                    "para_keyword":  rec.get("para_keyword", ""),
                    "insert_offset": rec.get("insert_offset", 2),
                })
            placeholders[sid] = ph

        return placeholders

    # ── python-docx 직접 작성 ────────────────────────────────
    def _direct_write(self, content: dict, template_path: str, output_path: str) -> dict:
        """BizPlanInjector 없이 python-docx로 직접 DOCX 생성."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        injector_content = self._build_injector_content(content)

        # ── 이미지 가이드는 콘솔 리포트로만 사용하고, 최종 DOCX에는 삽입하지 않음 ──
        self._build_image_placeholders(content)
        injector_content["image_slots"]        = content.get("image_slots", {})
        injector_content["image_placeholders"] = {}
        injector_content["blank_image_slots"]  = []

        # ── 데이터 삽입 후 남는 빈 행 제거 대상 표 목록 ──────────
        injector_content["trim_tables"] = [
            {"table_index": TABLE_INDEX["hire_plan"], "data_start_row": 1},
        ]

        stats = write_docx(template_path, output_path, injector_content)
        stats["dry_run"] = False
        if stats.get("errors"):
            print(f"  [DOCX_WRITER] 경고 {len(stats['errors'])}건:")
            for e in stats["errors"][:5]:
                print(f"    ⚠️  {e}")
        print(f"  [DOCX_WRITER] 완료 → {output_path}")
        print(f"    cells={stats['cells_written']}, sections={stats['sections_written']}, "
              f"images_inserted={stats.get('images_inserted', 0)}, "
              f"images_placeholder={stats.get('images_placeholder', 0)}, "
              f"blank_tables={stats.get('blank_tables_inserted', 0)}, "
              f"empty_rows_removed={stats.get('empty_rows_removed', 0)}")

        # ── STEP 5: 서식 자동화 (타이틀 볼드 + 중요 텍스트 강조) ─
        fmt_stats = {"title_bolded": 0}
        if FORMATTER_AVAILABLE:
            from docx import Document as _Doc
            doc_for_fmt = _Doc(output_path)
            fmt_stats   = apply_formatting(doc_for_fmt, content)
            doc_for_fmt.save(output_path)
            print(f"  [FORMATTER] title_bolded={fmt_stats['title_bolded']}")
        stats["title_bolded"] = fmt_stats.get("title_bolded", 0)

        self._stats = stats
        content["_render_stats"] = stats
        return stats

    # ── 드라이런 ─────────────────────────────────────────────
    def _dry_run(self, content: dict, template_path: str, output_path: str) -> dict:
        import json
        dry_path = output_path.replace(".docx", "_DRY_RUN.json")
        os.makedirs(os.path.dirname(dry_path) or ".", exist_ok=True)
        with open(dry_path, "w", encoding="utf-8") as f:
            safe = {k: v for k, v in content.items() if not k.startswith("_")}
            json.dump(safe, f, ensure_ascii=False, indent=2)
        print(f"  [DRY RUN] BizPlanInjector 미설치. 내용 검증 파일 저장: {dry_path}")
        stats = {"dry_run": True, "output": dry_path}
        content["_render_stats"] = stats
        return stats

    # ── 상태 요약 ──────────────────────────────────────────────
    def summary(self) -> str:
        if self._stats.get("dry_run"):
            return f"dry_run=True, output={self._stats.get('output')}"
        return (f"cells_written={self._stats.get('cells_written', '?')}, "
                f"sections_written={self._stats.get('sections_written', '?')}, "
                f"images_injected={self._stats.get('images_injected', 0)}")
