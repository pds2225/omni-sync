"""
formatter.py — DOCX 서식 자동화 (볼드·밑줄)
=============================================
역할: 완성된 DOCX 파일에 타이틀 볼드 및 수치 밑줄 서식을 적용.
      render_agent._direct_write() 의 마지막 단계에서 호출.

공개 함수:
    apply_formatting(doc_path) -> {"title_bolded": int}
        ① ①②③+콜론 패턴 → 콜론까지 볼드
        ② 가나다 헤딩 패턴 → 전체 볼드
        ③ 글머리 기호(· • ▶ - *)는 볼드 제외

    apply_underline(doc_path) -> {"underline_runs": int}
        수치+단위 패턴, 핵심 키워드 구문 → 밑줄 (볼드 없음)
        ※ 현재 파이프라인에서는 미호출 — 필요 시 render_agent에서 활성화

서식 보존 규칙:
    - 원본의 흰색(ffffff) 텍스트: 색상 유지
    - 원본의 이탤릭(※ 주석): 유지
    - 새로 삽입된 텍스트: 색상 000000, 이탤릭 제거
"""
from __future__ import annotations

import re
from typing import List, Tuple
from copy import deepcopy

from docx          import Document
from docx.oxml.ns  import qn
from docx.oxml     import OxmlElement


# ════════════════════════════════════════════════════════════════
# A. 타이틀 볼드 패턴
# ════════════════════════════════════════════════════════════════

_CIRCLE_NUM = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮"
_RE_CIRCLE_TITLE = re.compile(
    rf"^([{_CIRCLE_NUM}][^\n:：]*[:：])\s*(.*)",
    re.UNICODE,
)

_RE_GANA_TITLE = re.compile(
    r"^([가나다라마바사아자차카타파하]\.\s*[^\n]+)",
    re.UNICODE,
)

_RE_BULLET = re.compile(r"^[·•\-\*]\s")


# ════════════════════════════════════════════════════════════════
# B. 밑줄 패턴 (단독 밑줄만 — 볼드 없음)
# ════════════════════════════════════════════════════════════════

_RE_NUMBER_UNIT = re.compile(
    r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
    r"(%|조\s*원|억\s*원|만\s*원|개사?|건|명|배|시간|년|개월|%p|점)",
    re.UNICODE,
)

_KEY_PHRASES = [
    r"경쟁사?\s*대비\s*\d+배",
    r"주당\s*평균\s*\d+시간",
    r"정확도\s*\d+%",
    r"성장률\s*\d+%",
    r"\d+%\s*이상",
    r"(\d+,?\d*)\s*억?\s*원",
    r"전국\s*커버리지",
    r"AI\s*매칭",
    r"HS\s*Code",
    r"데이터\s*파이프라인",
    r"구독\s*요금",
    r"화이트라벨",
    r"M\+\d+",
]
_RE_KEY_PHRASES = re.compile(
    "|".join(f"({p})" for p in _KEY_PHRASES),
    re.UNICODE,
)


# ════════════════════════════════════════════════════════════════
# XML 헬퍼
# ════════════════════════════════════════════════════════════════

def _set_run_bold(run_elem):
    """run에 볼드 서식 추가."""
    rpr = run_elem.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        run_elem.insert(0, rpr)
    if rpr.find(qn("w:b")) is None:
        b = OxmlElement("w:b")
        rpr.append(b)
    if rpr.find(qn("w:bCs")) is None:
        bcs = OxmlElement("w:bCs")
        rpr.append(bcs)


def _set_run_underline(run_elem, val: str = "single"):
    """run에 밑줄 서식 추가 (볼드 없음)."""
    rpr = run_elem.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        run_elem.insert(0, rpr)
    u = rpr.find(qn("w:u"))
    if u is None:
        u = OxmlElement("w:u")
        rpr.append(u)
    u.set(qn("w:val"), val)


def _para_full_text(p_elem) -> str:
    return "".join((t.text or "") for t in p_elem.iter(qn("w:t")))


def _count_bold_runs(p_elem) -> int:
    cnt = 0
    for r in p_elem.findall(qn("w:r")):
        rpr = r.find(qn("w:rPr"))
        if rpr is not None and rpr.find(qn("w:b")) is not None:
            cnt += 1
    return cnt


# ════════════════════════════════════════════════════════════════
# A. 타이틀 볼드 처리
# ════════════════════════════════════════════════════════════════

def _apply_title_bold_to_para(p_elem):
    """단락에 타이틀 볼드 패턴 적용."""
    full = _para_full_text(p_elem).strip()
    if not full:
        return

    if _RE_BULLET.match(full):
        return

    # ①②③ + 콜론
    m = _RE_CIRCLE_TITLE.match(full)
    if m:
        title_part = m.group(1)
        _bold_runs_matching_prefix(p_elem, title_part)
        return

    # 가나다 헤딩
    m2 = _RE_GANA_TITLE.match(full)
    if m2:
        for run in p_elem.findall(qn("w:r")):
            _set_run_bold(run)
        return


def _bold_runs_matching_prefix(p_elem, title_part: str):
    """단락 앞부분(title_part 길이만큼)의 runs를 볼드 처리."""
    remaining = len(title_part.strip())
    for run in p_elem.findall(qn("w:r")):
        if remaining <= 0:
            break
        t_elem = run.find(qn("w:t"))
        if t_elem is None:
            continue
        txt = t_elem.text or ""
        if txt.strip():
            _set_run_bold(run)
            remaining -= len(txt)


# ════════════════════════════════════════════════════════════════
# B. 밑줄 처리 (run 분할 방식, 볼드 없음)
# ════════════════════════════════════════════════════════════════

def _apply_underline_to_para(p_elem):
    """
    단락에서 수치·핵심구문을 찾아 밑줄만 처리.
    run 분할 방식 — 기존 runs를 제거하고 매칭/비매칭 구간으로 재분할.
    """
    runs = p_elem.findall(qn("w:r"))
    if not runs:
        return

    full_text = ""
    run_spans: List[Tuple[int, int, object]] = []
    for r in runs:
        t = r.find(qn("w:t"))
        s = t.text or "" if t is not None else ""
        run_spans.append((len(full_text), len(full_text) + len(s), r))
        full_text += s

    if not full_text.strip():
        return

    # 밑줄 구간 탐지
    ul_ranges: List[Tuple[int, int]] = []
    for pat in [_RE_NUMBER_UNIT, _RE_KEY_PHRASES]:
        for m in pat.finditer(full_text):
            s, e = m.start(), m.end()
            merged = False
            for i, (es, ee) in enumerate(ul_ranges):
                if not (e <= es or s >= ee):
                    ul_ranges[i] = (min(es, s), max(ee, e))
                    merged = True
                    break
            if not merged:
                ul_ranges.append((s, e))

    if not ul_ranges:
        return

    ul_ranges.sort()

    # 전체 구간 목록 (밑줄/비밑줄)
    segments: List[Tuple[int, int, bool]] = []
    prev = 0
    for us, ue in ul_ranges:
        if prev < us:
            segments.append((prev, us, False))
        segments.append((us, ue, True))
        prev = ue
    if prev < len(full_text):
        segments.append((prev, len(full_text), False))

    # 참조 rPr 수집 후 기존 runs 제거
    ref_rpr = None
    for r in runs:
        rpr = r.find(qn("w:rPr"))
        if ref_rpr is None and rpr is not None:
            ref_rpr = deepcopy(rpr)
        p_elem.remove(r)

    # 새 runs 삽입
    for (seg_start, seg_end, is_ul) in segments:
        seg_text = full_text[seg_start:seg_end]
        if not seg_text:
            continue

        new_r = OxmlElement("w:r")

        # rPr 복사
        rpr_copy = deepcopy(ref_rpr) if ref_rpr is not None else OxmlElement("w:rPr")

        # 색상=검정, 이탤릭 제거 (서식 초기화)
        col_elem = rpr_copy.find(qn("w:color"))
        if col_elem is None:
            col_elem = OxmlElement("w:color")
            rpr_copy.append(col_elem)
        col_elem.set(qn("w:val"), "000000")
        for tag in ("w:i", "w:iCs"):
            it = rpr_copy.find(qn(tag))
            if it is not None:
                rpr_copy.remove(it)

        if is_ul:
            # 밑줄만 추가 (볼드 없음)
            u = rpr_copy.find(qn("w:u"))
            if u is None:
                u = OxmlElement("w:u")
                rpr_copy.append(u)
            u.set(qn("w:val"), "single")

        new_r.append(rpr_copy)

        new_t = OxmlElement("w:t")
        new_t.text = seg_text
        if seg_text != seg_text.strip() or seg_text.startswith(" ") or seg_text.endswith(" "):
            new_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        new_r.append(new_t)
        p_elem.append(new_r)


# ════════════════════════════════════════════════════════════════
# 진입점
# ════════════════════════════════════════════════════════════════

def apply_formatting(doc: Document, content: dict = None) -> dict:
    """
    A. 타이틀 볼드만 적용 (①/가나다 헤딩).
    밑줄은 apply_underline() 으로 별도 호출.

    Returns:
        {"title_bolded": int}
    """
    title_bolded = 0

    def _process(p_elem):
        nonlocal title_bolded
        full = _para_full_text(p_elem).strip()
        if not full:
            return
        before = _count_bold_runs(p_elem)
        _apply_title_bold_to_para(p_elem)
        after  = _count_bold_runs(p_elem)
        if after > before:
            title_bolded += 1

    for p in doc.element.body.findall(qn("w:p")):
        _process(p)

    for tbl in doc.element.body.iter(qn("w:tbl")):
        for p in tbl.iter(qn("w:p")):
            _process(p)

    return {"title_bolded": title_bolded}


def apply_underline(doc: Document) -> dict:
    """
    B. 수치·핵심구문에 밑줄만 적용 (볼드 없음).
    필요 시 apply_formatting() 이후 별도로 호출.

    Returns:
        {"underline_paras": int}
    """
    ul_paras = 0

    def _process(p_elem):
        nonlocal ul_paras
        full = _para_full_text(p_elem).strip()
        if not full:
            return
        _apply_underline_to_para(p_elem)
        ul_paras += 1

    for p in doc.element.body.findall(qn("w:p")):
        _process(p)

    for tbl in doc.element.body.iter(qn("w:tbl")):
        for p in tbl.iter(qn("w:p")):
            _process(p)

    return {"underline_paras": ul_paras}
