"""
orchestrator.py
---------------
데이터바우처 사업계획서 자동작성 — 총괄 오케스트레이터

실행 순서:
  1. company_master.json + project_input.json → 통합 content 구성
  2. WriterAgent    — 서술형 섹션 문안 생성
  3. TableAgent     — 사업비/일정/인력 표 구조화
  4. AssetAgent     — 이미지 경로·제목 정리
  5. ImageAdvisor   — 섹션별 이미지 추천 텍스트 + 위치 생성
  6. RenderAgent    — DOCX 실제 삽입 (BizPlanInjector 호출)
  7. QAAgent        — 누락·불일치·제약 위반 검사 후 리포트 출력

사용법:
    python orchestrator.py \
        --master  data/company_master.json \
        --project data/project_input.json \
        --template templates/datavoucher_2026.docx \
        --output   output/사업계획서_완성.docx
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 에이전트 임포트
from agents.writer_agent import WriterAgent
from agents.table_agent  import TableAgent
from agents.asset_agent  import AssetAgent
from agents.render_agent import RenderAgent
from agents.qa_agent     import QAAgent


# ── 유틸 ─────────────────────────────────────────────────────────
def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_content(master: dict, project: dict) -> dict:
    """
    company_master + project_input을 하나의 content 딕셔너리로 병합.

    우선순위: project 값 > master 값
    최종 구조는 BizPlanInjector 의 content.json 포맷과 동일.
    """
    content = {}

    # ── master 레이어 병합 ──────────────────────────────────────
    content["company"]         = master.get("company", {})
    content["ceo"]             = master.get("ceo", {})
    content["core_competency"] = master.get("core_competency", [])

    # ── project 레이어 병합 ─────────────────────────────────────
    content["meta"]         = project.get("meta", {})
    content["narrative"]    = project.get("narrative", {})
    content["budget_mix"]   = project.get("budget_mix", {})
    content["budget_total"] = project.get("budget_total", 0)
    content["schedule"]     = project.get("schedule", [])
    content["team"]         = project.get("team", [])
    content["assets"]       = project.get("assets", [])
    content["privacy"]      = project.get("privacy", {})
    content["hire_plan"]    = project.get("hire_plan", [])
    content["comparison_tables"] = project.get("comparison_tables", [])

    return content


def banner(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def configure_console_encoding():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


# ── 메인 파이프라인 ────────────────────────────────────────────────
class Orchestrator:
    """
    5개 에이전트를 순서대로 호출하고, 각 단계 결과를 다음 단계로 전달.

    각 에이전트는 독립적으로 교체 가능하도록 인터페이스를 통일했습니다.
    - run(content) → 수정된 content 반환  (Writer / Table / Asset)
    - run(content, template, output) → stats 반환  (Render)
    - run(content, output_docx) → QAReport 반환  (QA)
    """

    def __init__(self, master_path: str, project_path: str,
                 template_path: str, output_path: str,
                 llm_enabled: bool = False):
        self.master_path   = master_path
        self.project_path  = project_path
        self.template_path = template_path
        self.output_path   = output_path
        self.llm_enabled   = llm_enabled  # Phase 3 이후 활성화
        self.log           = []

    def _record(self, stage: str, result):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = {"time": ts, "stage": stage, "result": result}
        self.log.append(entry)
        print(f"  [{ts}] {stage}: {result}")

    def run(self) -> dict:
        banner("STEP 0 — 입력 데이터 로드 및 병합")
        master  = load_json(self.master_path)
        project = load_json(self.project_path)
        content = merge_content(master, project)
        self._record("data_merge", f"company={content['company']['name']}, "
                     f"project={content['meta']['project_title'][:20]}...")

        # ── STEP 1: 서술형 문안 생성 ─────────────────────────────
        banner("STEP 1 — WriterAgent: 서술형 섹션 문안 생성")
        writer  = WriterAgent(llm_enabled=self.llm_enabled)
        content = writer.run(content)
        self._record("WriterAgent", writer.summary())

        # ── STEP 2: 표 데이터 구조화 ─────────────────────────────
        banner("STEP 2 — TableAgent: 사업비/일정/인력 표 구조화")
        table   = TableAgent()
        content = table.run(content)
        self._record("TableAgent", table.summary())

        # ── STEP 3: 이미지 정리 ──────────────────────────────────
        banner("STEP 3 — AssetAgent: 이미지 경로·제목 정리")
        asset   = AssetAgent()
        content = asset.run(content)
        self._record("AssetAgent", asset.summary())

        # ── STEP 4: DOCX 렌더링 (ImageAdvisor는 내부 호출) ──────
        banner("STEP 4 — RenderAgent: DOCX 삽입 + 이미지 추천 텍스트 삽입")
        render  = RenderAgent()
        stats   = render.run(content, self.template_path, self.output_path)
        self._record("RenderAgent", stats)

        # ── STEP 5: QA 검사 ──────────────────────────────────────
        banner("STEP 5 — QAAgent: 누락·불일치·제약 위반 검사")
        qa      = QAAgent()
        report  = qa.run(content, self.output_path)
        self._record("QAAgent", f"errors={report['error_count']}, "
                     f"warnings={report['warning_count']}")

        # ── 최종 요약 ────────────────────────────────────────────
        banner("완료 — 최종 요약")
        print(f"  출력 파일  : {self.output_path}")
        print(f"  QA 오류    : {report['error_count']}건")
        print(f"  QA 경고    : {report['warning_count']}건")
        if report["errors"]:
            print("\n  [오류 목록]")
            for e in report["errors"]:
                print(f"    ❌ {e}")
        if report["warnings"]:
            print("\n  [경고 목록]")
            for w in report["warnings"]:
                print(f"    ⚠️  {w}")

        # QA 리포트 파일 저장
        report_path = self.output_path.replace(".docx", "_QA리포트.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({"log": self.log, "qa": report}, f, ensure_ascii=False, indent=2)
        print(f"\n  QA 리포트  : {report_path}")

        return {"stats": stats, "qa": report, "output": self.output_path}


# ── CLI 진입점 ────────────────────────────────────────────────────
def main():
    configure_console_encoding()
    parser = argparse.ArgumentParser(
        description="데이터바우처 사업계획서 자동작성 엔진"
    )
    parser.add_argument("--master",   default="data/company_master.json",
                        help="기업 마스터 데이터 경로")
    parser.add_argument("--project",  default="data/project_input.json",
                        help="과제 입력 데이터 경로")
    parser.add_argument("--template", default="templates/datavoucher_2026.docx",
                        help="원본 DOCX 양식 경로")
    parser.add_argument("--output",   default="output/사업계획서_완성.docx",
                        help="출력 DOCX 파일 경로")
    parser.add_argument("--llm",      action="store_true",
                        help="LLM 문안 생성 활성화 (Phase 3 이상)")
    args = parser.parse_args()

    # 출력 디렉토리 자동 생성
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    orchestrator = Orchestrator(
        master_path   = args.master,
        project_path  = args.project,
        template_path = args.template,
        output_path   = args.output,
        llm_enabled   = args.llm,
    )
    result = orchestrator.run()

    # QA 오류가 있으면 exit code 1
    if result["qa"]["error_count"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
