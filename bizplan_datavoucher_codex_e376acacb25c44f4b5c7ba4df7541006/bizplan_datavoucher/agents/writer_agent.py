"""
writer_agent.py — 서술형 텍스트 → 개조식 불릿 변환
======================================================
역할: project_input.json의 narrative 값을 사업계획서용 개조식 문체로 변환.

주요 공개 인터페이스:
    WriterAgent(bullet_convert=True).run(content) -> content
        content["narrative"][key] 를 in-place 수정하고 반환.

핵심 함수 호출 순서:
    to_bullet(text)
      └─ _split_into_sentences(text)   # 마침표/쉼표 복합절 기준 문장 분리
      └─ _convert_ending(sentence)     # 3단계: 전처리→어미변환→조사후처리
           ├─ STAGE 1: 복합 종결어미 전처리 (_STAGE1_PRE)
           ├─ STAGE 2: _ENDING_REPLACE_V5 패턴 적용
           └─ STAGE 3: _POST_CLEANUP 조사 제거

변환하지 않을 필드: narrative 키 중 구조화 텍스트(예: budget_rationale, solution)는
    WriterAgent 초기화 시 BULLET_SKIP_FIELDS 에 추가하면 변환 건너뜀.
    현재: 모든 키 변환 적용 중 → TODO: BULLET_SKIP_FIELDS 구현 필요

테스트: writer_agent.py 실행 시 27개 케이스 자동 검증
    python agents/writer_agent.py
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
    "alliance_plan": [
        "· 제휴처 1: 기관명 — 협력 내용 및 기대 효과",
        "· 제휴처 2: 기관명 — 협력 내용 및 기대 효과",
        "· 제휴처 3: 기관명 — 협력 내용 및 기대 효과",
    ],
    "pr_plan": [
        "· 온라인: 광고채널 — 목표 도달수",
        "· 콘텐츠: 발행 형태 — 구독자 목표",
        "· 오프라인: 행사/전시 — 접촉 기업 수",
        "· KPI: 가입 기업 N개사 확보, 월 매출 N만 원 달성",
    ],
    "future_plan": [
        "· 6개월 이후: 단기 목표",
        "· 1년 이후: 중기 목표",
        "· 2년 이후: 장기 목표/확장 방향",
    ],
    "output_plan": [
        "· 공개 범위: 데이터셋 종류 및 비식별 처리 여부",
        "· 활용 방안: API 제공 또는 오픈데이터 포털 등록",
        "· 라이선스: 활용 조건",
    ],
    "output_effect": [
        "· 직접 효과: 수혜 기업 수 / 시간 절감 수치",
        "· 간접 효과: 사회적 가치 / 2차 활용",
        "· 목표: 누적 활용 기업 N개사",
    ],
}

BULLET_SKIP_FIELDS = {
    "solution",
    "budget_rationale",
}


# ════════════════════════════════════════════════════════════════
# 개조식 변환 유틸리티
#
# 3단계 파이프라인:
#   STAGE 1: 복합 종결어미 전처리
#     1-A  조동사 복합형:  검토해야 한다 → 검토
#     1-B  상태/실정 명사: 구축 완료 상태다 → 구축 완료
#                         발생하는 실정이다 → 발생 실태
#     1-C  연결어미 종결:  정형화하고, → 정형화  (절 단독 끝)
#   STAGE 2: 기존 종결어미 패턴 (한다/합니다/됩니다 등)
#   STAGE 3: 조사 후처리  (을/를/도 잔류 제거, 에 달 → 수준)
# ════════════════════════════════════════════════════════════════

_ENDING_REPLACE = [
    # ─ STAGE 1-A: 조동사 복합형 (우선 처리) ──────────────────
    # "[동사어간]해야/하여야 한다/합니다" → "[동사어간]"
    # 예) 검토해야 한다 → 검토,  수행해야 합니다 → 수행
    (r'([가-힣]+)(?:해야|하여야)\s*(?:한다|합니다|할 것이다)\.?\s*$', r'\1'),

    # ─ STAGE 1-B: 상태/실정 명사 치환 ────────────────────────
    # "[선행어 공백] 상태다" → "[선행어]"
    # 비탐욕 + 앞 공백 분리로 내부 공백 보존
    # 예) 구축 완료 상태다 → 구축 완료 / 이미 구현 완료 상태다 → 이미 구현 완료
    (r'([가-힣\s]+?)\s+상태다\.?\s*$',         r'\1'),
    # "[동사어간]하는 실정이다" → "[동사어간] 실태"
    # 예) 발생하는 실정이다 → 발생 실태
    (r'([가-힣]+)하는\s*실정이다\.?\s*$',        r'\1 실태'),
    # 단독 "실정이다" → "실태"
    (r'실정이다\.?\s*$',                          '실태'),
    # "~인/한/는/을 상황이다" → 상황 어구 제거
    (r'\s*(?:인|한|는|을)\s*상황이다\.?\s*$',    ''),
    # "~중이다" → "~중"
    (r'\s*중이다\.?\s*$',                         ' 중'),

    # ─ STAGE 1-C: 연결어미 종결 (절 단독 끝일 때만) ──────────
    # 쉼표 유무 통합: "정형화하고," or "처리하며" (뒤에 내용 없을 때)
    # 복합절("처리하고, 다음절")은 _split_into_sentences에서 분리 후 처리
    (r'([가-힣]+)(?:하고|하며),?\s*$',           r'\1'),

    # ─ STAGE 2: 존댓말 종결어미 ──────────────────────────────
    (r'합니다\.?\s*$',        ''),
    (r'했습니다\.?\s*$',      ''),
    (r'됩니다\.?\s*$',        ''),
    (r'됐습니다\.?\s*$',      ''),
    (r'있습니다\.?\s*$',      ''),
    (r'입니다\.?\s*$',        ''),
    # ─ STAGE 2: 평서형 종결어미 ──────────────────────────────
    (r'한다\.?\s*$',          ''),
    (r'된다\.?\s*$',          ''),
    (r'있다\.?\s*$',          ''),
    (r'이다\.?\s*$',          ''),
    (r'였다\.?\s*$',          ''),
    (r'했다\.?\s*$',          ''),
    # ─ STAGE 2: 예정/계획/목표 ───────────────────────────────
    (r'예정이다\.?\s*$',      '예정'),
    (r'계획이다\.?\s*$',      '계획'),
    (r'목표이다\.?\s*$',      '목표'),
    (r'목표다\.?\s*$',        '목표'),
    (r'할 예정이다\.?\s*$',   '예정'),
    # ─ STAGE 2: 동작 동사 → 명사형 ──────────────────────────
    (r'하고자 한다\.?\s*$',   '추진'),
    (r'추진한다\.?\s*$',      '추진'),
    (r'추진합니다\.?\s*$',    '추진'),
    (r'구축한다\.?\s*$',      '구축'),
    (r'구축합니다\.?\s*$',    '구축'),
    (r'개발한다\.?\s*$',      '개발'),
    (r'개발합니다\.?\s*$',    '개발'),
    (r'운영한다\.?\s*$',      '운영'),
    (r'운영합니다\.?\s*$',    '운영'),
    (r'제공한다\.?\s*$',      '제공'),
    (r'제공합니다\.?\s*$',    '제공'),
    (r'제공받는다\.?\s*$',    '제공 받음'),
    (r'제공받습니다\.?\s*$',  '제공 받음'),
    (r'달성한다\.?\s*$',      '달성'),
    (r'달성합니다\.?\s*$',    '달성'),
    (r'달성할 예정\.?\s*$',   '달성 예정'),
    (r'확보한다\.?\s*$',      '확보'),
    (r'확보합니다\.?\s*$',    '확보'),
    (r'확보할 예정\.?\s*$',   '확보 예정'),
    (r'향상된다\.?\s*$',      '향상'),
    (r'기대된다\.?\s*$',      '기대'),
    (r'연계한다\.?\s*$',      '연계'),
    (r'연계합니다\.?\s*$',    '연계'),
    (r'확장한다\.?\s*$',      '확장'),
    (r'확장합니다\.?\s*$',    '확장'),
    (r'병행한다\.?\s*$',      '병행'),
    (r'병행합니다\.?\s*$',    '병행'),
    (r'추천한다\.?\s*$',      '추천'),
    (r'추천합니다\.?\s*$',    '추천'),
    (r'분류·추천한다\.?\s*$', '분류·추천'),
    # "~에 달한다/달합니다" → "~수준" (관용 표현)
    (r'달한다\.?\s*$',        '수준'),
    (r'달합니다\.?\s*$',      '수준'),
    # ─ 마침표 제거 (위 규칙에 걸리지 않은 경우) ─────────────
    (r'\.\s*$',               ''),
]

# ── STAGE 3: 조사 후처리 ─────────────────────────────────────
# STAGE 2로 동사어간을 추출했지만 선행 조사가 잔류하는 경우 제거
# 예) "5건을 제공" → "5건 제공"  /  "공급)도 병행" → "공급) 병행"
_POST_CLEANUP = [
    # 목적격 조사 [을/를] + 동사/명사어$ → 조사 제거
    # 앞이 공백이든 한글/숫자이든 모두 처리
    (r'[을를]\s+([가-힣]+(?:\s+[가-힣]+)?)\s*$',    r' \1'),
    # 보조사 '도' + 닫는 괄호 잔류
    (r'\)\s*도\s+([가-힣]+)\s*$',                    r') \1'),
    (r'\s+도\s+([가-힣]+)\s*$',                      r' \1'),
    # "에 달" → 수준 (달하다 어간 + 조사 잔류)
    (r'\s*에\s*달\s*$',                              ' 수준'),
    # 잔류 해야/하여야 (STAGE 1-A 이후)
    (r'\s*해야\s*$',                                 ''),
    (r'\s*하여야\s*$',                               ''),
    # 주격조사 잔류
    (r'\s+[이가]\s+([가-힣]+)\s*$',                  r' \1'),
]

_BULLET_PREFIX = r'^[\·\•\○\●\-\*\①-\⑳\ⓐ-\ⓩ\d+\.] *'


def _split_into_sentences(text: str) -> list[str]:
    """
    한 줄에 여러 문장이 마침표·연결어미로 이어진 경우 개별 문장으로 분리.

    분리 기준:
      1. 종결어미(다/있/었/함/됨/음/임) + 마침표(.) + 공백 또는 문장 끝
      2. "~하고, [한글]" 복합 연결절 (쉼표+공백+한글)
      3. "~하며, [한글]" 복합 연결절

    예외 (분리 안 함):
      - 숫자 소수점 (3.14)
      - 영어 약어 (U.S., No.)
      - 닫는 괄호 직전 마침표

    이미 \n이 있으면 \n 기준 분리만 수행.
    """
    if "\n" in text:
        return [s for s in text.split("\n")]

    # 종결어미+마침표 패턴
    sentence_end = re.compile(
        r'(?<=[다있었함됨음임됨])\.(?=\s|$)'    # 종결어미+마침표
        r'|(?<=하고,)(?=\s[가-힣])'             # 하고, 뒤 새 주어절
        r'|(?<=하며,)(?=\s[가-힣])',             # 하며, 뒤 새 주어절
        re.UNICODE
    )
    parts = sentence_end.split(text)

    result = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # "A하고, B" / "A하며, B" 복합절 분리 (B가 한글로 시작할 때)
        m = re.match(r'^(.+[가-힣](?:하고|하며)),\s*([가-힣].+)$', p)
        if m:
            result.append(m.group(1))   # A하고 부분
            result.append(m.group(2))   # B 부분
        else:
            result.append(p)
    return result


def _convert_ending(line: str) -> str:
    """
    종결어미를 명사형으로 변환 (3단계 파이프라인 적용).

    STAGE 1+2: _ENDING_REPLACE 패턴 순차 적용 (첫 매칭에서 중단)
    STAGE 3:   _POST_CLEANUP 후처리 (조사 잔류 제거)
    """
    s = line.rstrip()

    # STAGE 1 + STAGE 2
    for pattern, repl in _ENDING_REPLACE:
        if callable(repl):
            continue
        new_s = re.sub(pattern, repl, s)
        if new_s != s:
            s = new_s.rstrip()
            break

    # STAGE 3: 조사 후처리 (모든 규칙 적용)
    for pattern, repl in _POST_CLEANUP:
        new_s = re.sub(pattern, repl, s)
        if new_s != s:
            s = new_s.rstrip()

    return s


def to_bullet(text: str, prefix: str = "· ") -> str:
    """
    서술형 텍스트를 개조식으로 변환합니다.

    규칙:
      1. 줄 단위로 분리 (\n 없으면 마침표·연결어미 기준 자동 분리)
      2. 이미 불릿(·, •, ①…) 으로 시작하는 줄은 어미 변환만 적용
      3. 불릿 없는 줄에는 prefix(기본 '· ') 추가
      4. _convert_ending으로 서술형 종결어미 → 명사형 변환
      5. 절 끝의 잔류 쉼표 제거 후 각 절을 별도 불릿으로 분리

    Args:
        text:   원본 텍스트 (줄바꿈 구분)
        prefix: 접두어 (기본 '· ')

    Returns:
        개조식 변환된 텍스트

    Examples:
        >>> to_bullet("파일럿 기업 30개사 대상 서비스를 제공합니다.")
        '· 파일럿 기업 30개사 대상 서비스 제공'

        >>> to_bullet("검토해야 한다")
        '· 검토'

        >>> to_bullet("처리하고, 저장")
        '· 처리\n· 저장'

        >>> to_bullet("연 1.2조 원에 달한다")
        '· 연 1.2조 원 수준'
    """
    # 복합 문장 분리 (마침표·연결어미 기준)
    lines = _split_into_sentences(text)

    result = []
    for line in lines:
        stripped = line.strip().rstrip(',')   # 절 끝 쉼표 제거
        if not stripped:
            result.append('')
            continue

        converted = _convert_ending(stripped)

        has_bullet = bool(re.match(_BULLET_PREFIX, converted))
        if has_bullet:
            result.append(re.sub(r'^\s+', '', converted))
        else:
            result.append(f'{prefix}{converted}')

    return "\n".join(result)


class WriterAgent:
    """
    서술형 섹션 문안 생성 에이전트.

    run(content) → content  (narrative 섹션을 채운 뒤 반환)

    bullet_convert=True (기본) 이면 모든 narrative 텍스트를 개조식으로 변환.
    """

    def __init__(self, llm_enabled: bool = False,
                 prompts_dir: str = "prompts",
                 bullet_convert: bool = True):
        self.llm_enabled    = llm_enabled
        self.prompts_dir    = prompts_dir
        self.bullet_convert = bullet_convert
        self._filled:   list[str] = []
        self._skipped:  list[str] = []
        self._bulleted: list[str] = []

    # ── 메인 실행 ──────────────────────────────────────────────
    def run(self, content: dict) -> dict:
        narrative = content.get("narrative", {})
        company   = content.get("company", {})
        meta      = content.get("meta", {})

        for field, rules in WRITING_RULES.items():
            existing = narrative.get(field, "").strip()
            if existing:
                if self.bullet_convert and field not in BULLET_SKIP_FIELDS:
                    converted = to_bullet(existing)
                    narrative[field] = converted
                    self._bulleted.append(field)
                else:
                    self._skipped.append(field)
                continue

            if self.llm_enabled:
                text = self._generate_with_llm(field, content)
            else:
                text = self._generate_template(field, rules, company, meta)

            if self.bullet_convert and field not in BULLET_SKIP_FIELDS:
                text = to_bullet(text)

            narrative[field] = text
            self._filled.append(field)

        content["narrative"] = narrative
        return content

    # ── 템플릿 기반 생성 (Phase 1 MVP) ─────────────────────────
    def _generate_template(self, field: str, rules: list,
                            company: dict, meta: dict) -> str:
        lines = [f"[{field.upper()} 초안 — 아래 구조에 맞게 작성하세요]\n"]
        for i, rule in enumerate(rules, 1):
            rule = rule.replace("{industry}", company.get("industry", "[업종]"))
            rule = rule.replace("{project_title}", meta.get("project_title", "[과제명]"))
            lines.append(f"{i}. {rule}")
        return "\n".join(lines)

    # ── LLM 기반 생성 (Phase 3) ────────────────────────────────
    def _generate_with_llm(self, field: str, content: dict) -> str:
        prompt_path = os.path.join(self.prompts_dir, f"{field}.txt")
        if not os.path.exists(prompt_path):
            return self._generate_template(
                field,
                WRITING_RULES.get(field, ["[내용을 작성하세요]"]),
                content.get("company", {}),
                content.get("meta", {})
            )
        raise NotImplementedError("LLM 생성 기능은 Phase 3에서 활성화됩니다.")

    # ── 상태 요약 ──────────────────────────────────────────────
    def summary(self) -> str:
        return (f"filled={len(self._filled)}{self._filled}, "
                f"skipped={len(self._skipped)}{self._skipped}, "
                f"bulleted={len(self._bulleted)}{self._bulleted}")
