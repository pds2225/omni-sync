"""
agents/writer_agent.py
-----------------------
서술형 섹션 문안 생성 에이전트

담당 섹션 (narrative 레이어):
  - problem         : 문제인식/추진배경/필요성
  - solution        : 실현방안/서비스 내용
  - market_status   : 시장현황/경쟁현황
  - bm_intro        : 수익모델/사업화 전략
  - differentiator  : 특장점/차별화 요소
  - expected_effect : 기대효과/향후계획

Phase 1 (MVP):
  - content["narrative"] 값이 이미 있으면 그대로 사용 (pass-through)
  - 비어 있는 항목만 구조 템플릿으로 자동 채우기

Phase 3 이후:
  - llm_enabled=True 시 각 항목을 LLM 프롬프트로 생성
  - prompts/ 폴더의 .txt 파일을 프롬프트 템플릿으로 사용
"""

from __future__ import annotations

import os
import re
from typing import Any


# ── 항목별 구조 작성 규칙 ────────────────────────────────────────
WRITING_RULES = {
    "problem": [
        "현황: {industry} 분야에서 발생하는 문제 상황",
        "문제: 핵심 불편/비효율 구체화",
        "손실: 정량적 손실 또는 기회비용",
        "필요성: 데이터 활용을 통한 해결 당위성",
    ],
    "solution": [
        "서비스 구조: 어떤 데이터를 어떻게 활용하는지",
        "차별성: 기존 방식 대비 무엇이 다른가",
        "구현 수준: 현재 개발 상태 또는 가능성",
        "실현 가능성: 기술·인력·파트너십 근거",
    ],
    "market_status": [
        "목표시장: TAM → SAM → SOM 구조로 규모 제시",
        "고객군: 주 타깃 기업/기관 특성",
        "경쟁현황: 유사 서비스 존재 여부 및 포지셔닝",
        "진입기회: 시장 성장률 또는 공백 근거",
    ],
    "bm_intro": [
        "수익모델: 과금 방식 (구독/건당/B2B 등)",
        "단가: 예상 객단가",
        "전환구조: 무료→유료 전환 경로",
        "매출화 경로: 영업/유통 채널",
    ],
    "differentiator": [
        "① 차별화 요소 1 (수치 포함)",
        "② 차별화 요소 2 (수치 포함)",
        "③ 차별화 요소 3 (수치 포함)",
    ],
    "expected_effect": [
        "단기(6개월): 핵심 KPI 목표치",
        "중기(12개월): 매출/사용자 목표",
        "장기(24개월): 시장 확장 방향",
    ],
}


class WriterAgent:
    """
    서술형 섹션 문안 생성 에이전트.

    run(content) → content  (narrative 섹션을 채운 뒤 반환)
    """

    def __init__(self, llm_enabled: bool = False, prompts_dir: str = "prompts"):
        self.llm_enabled = llm_enabled
        self.prompts_dir = prompts_dir
        self._filled: list[str] = []  # 실제로 채운 항목
        self._skipped: list[str] = []  # 이미 있어서 건너뛴 항목

    # ── 메인 실행 ──────────────────────────────────────────────
    def run(self, content: dict) -> dict:
        """
        content["narrative"] 각 항목을 순회하며,
        비어 있는 항목에만 문안을 생성해서 채웁니다.

        Args:
            content: 통합 content 딕셔너리 (merge_content 결과물)

        Returns:
            narrative가 채워진 content
        """
        narrative = content.get("narrative", {})
        company   = content.get("company", {})
        meta      = content.get("meta", {})

        for field, rules in WRITING_RULES.items():
            existing = narrative.get(field, "").strip()
            if existing:
                # 이미 값이 있으면 건드리지 않음
                self._skipped.append(field)
                continue

            if self.llm_enabled:
                text = self._generate_with_llm(field, content)
            else:
                text = self._generate_template(field, rules, company, meta)

            narrative[field] = text
            self._filled.append(field)

        content["narrative"] = narrative
        return content

    # ── 템플릿 기반 생성 (Phase 1 MVP) ─────────────────────────
    def _generate_template(self, field: str, rules: list,
                            company: dict, meta: dict) -> str:
        """
        작성 규칙(rules)을 문단 구조로 변환하여 초안 텍스트를 반환.
        실제 값이 없는 자리는 [대괄호 placeholder]로 표시.

        Args:
            field:   narrative 항목명
            rules:   해당 항목의 작성 구조 목록
            company: 기업 정보
            meta:    과제 메타 정보

        Returns:
            구조화된 초안 텍스트
        """
        lines = [f"[{field.upper()} 초안 — 아래 구조에 맞게 작성하세요]\n"]
        for i, rule in enumerate(rules, 1):
            # 알려진 값 자동 치환
            rule = rule.replace("{industry}", company.get("industry", "[업종]"))
            rule = rule.replace("{project_title}", meta.get("project_title", "[과제명]"))
            lines.append(f"{i}. {rule}")
        return "\n".join(lines)

    # ── LLM 기반 생성 (Phase 3) ────────────────────────────────
    def _generate_with_llm(self, field: str, content: dict) -> str:
        """
        Phase 3 이후 활성화. prompts/{field}.txt를 읽어 LLM API 호출.

        현재는 NotImplementedError 대신 _generate_template fallback.
        """
        prompt_path = os.path.join(self.prompts_dir, f"{field}.txt")
        if not os.path.exists(prompt_path):
            # 프롬프트 파일 없으면 템플릿 방식으로 대체
            return self._generate_template(
                field,
                WRITING_RULES.get(field, ["[내용을 작성하세요]"]),
                content.get("company", {}),
                content.get("meta", {})
            )
        # TODO: LLM API 호출 로직 삽입
        # prompt_template = open(prompt_path, encoding="utf-8").read()
        # filled_prompt = prompt_template.format(**content)
        # return llm_client.generate(filled_prompt)
        raise NotImplementedError("LLM 생성 기능은 Phase 3에서 활성화됩니다.")

    # ── 상태 요약 ──────────────────────────────────────────────
    def summary(self) -> str:
        return (f"filled={len(self._filled)}{self._filled}, "
                f"skipped={len(self._skipped)}{self._skipped}")
