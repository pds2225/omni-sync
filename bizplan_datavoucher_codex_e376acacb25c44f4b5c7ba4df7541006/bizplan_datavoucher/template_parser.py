"""
template_parser.py
-------------------
DOCX 양식 구조 자동 분석 스크립트

사용법:
    python template_parser.py --docx templates/datavoucher_2026.docx

출력:
    1. 표 인덱스 + 표 내 모든 셀 텍스트 (TABLE_INDEX 좌표 확정용)
    2. 단락 섹션 목록 (inject_after_keyword 키워드 확정용)
    3. template_map.json 자동 저장

이 파일을 한 번 실행하면 render_agent.py의
TABLE_INDEX / SECTION_KEYWORD 값을 정확히 채울 수 있습니다.
"""

import argparse
import json
import os
import zipfile
from lxml import etree

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS  = {"w": WNS}

def _w(tag): return f"{{{WNS}}}{tag}"

def para_text(p):
    return "".join(r.text or "" for r in p.iter(_w("t")))

def cell_text(cell):
    return " / ".join(
        para_text(p).strip()
        for p in cell.findall(_w("p"), NS)
        if para_text(p).strip()
    )

def is_blue_run(run):
    BLUE = {"4472c4","1f3864","2e74b5","4f81bd","17375e","244185",
            "1f497d","0070c0","2f5496","215868","1f5c8b","0000ff"}
    rPr = run.find(_w("rPr"), NS)
    if rPr is None: return False
    col = rPr.find(_w("color"), NS)
    if col is None: return False
    return col.get(_w("val"), "").lower() in BLUE


def analyze(docx_path: str) -> dict:
    """DOCX를 파싱하여 표·단락 구조를 반환."""
    # ZIP 에서 document.xml 추출
    with zipfile.ZipFile(docx_path, "r") as z:
        xml_bytes = z.read("word/document.xml")

    root = etree.fromstring(xml_bytes)
    body = root.find(_w("body"), NS)

    result = {
        "docx": docx_path,
        "tables": [],
        "sections": [],
        "blue_paragraphs": [],
    }

    tbl_idx = 0
    for elem in body:
        # ── 표 ──────────────────────────────────────────────────
        if elem.tag == _w("tbl"):
            tbl_info = {
                "table_index": tbl_idx,
                "rows": []
            }
            rows = elem.findall(_w("tr"), NS)
            for r_idx, row in enumerate(rows):
                cells = row.findall(_w("tc"), NS)
                row_info = []
                for c_idx, cell in enumerate(cells):
                    txt = cell_text(cell)
                    row_info.append({
                        "row": r_idx,
                        "cell": c_idx,
                        "text": txt[:60] + ("…" if len(txt) > 60 else "")
                    })
                tbl_info["rows"].append(row_info)
            result["tables"].append(tbl_info)
            tbl_idx += 1

        # ── 단락 ────────────────────────────────────────────────
        elif elem.tag == _w("p"):
            txt = para_text(elem).strip()
            if not txt:
                continue

            # 파란 안내문구 감지
            has_blue = any(is_blue_run(r) for r in elem.findall(_w("r"), NS))
            if has_blue:
                result["blue_paragraphs"].append(txt[:80])

            result["sections"].append({
                "text": txt[:80] + ("…" if len(txt) > 80 else ""),
                "is_blue": has_blue
            })

    return result


def print_report(data: dict):
    print("\n" + "=" * 70)
    print(f"  DOCX 구조 분석 리포트: {data['docx']}")
    print("=" * 70)

    print(f"\n[표 목록] — 총 {len(data['tables'])}개")
    for tbl in data["tables"]:
        idx = tbl["table_index"]
        print(f"\n  ┌── 표 #{idx} ({'총 ' + str(len(tbl['rows'])) + '행'})")
        for row in tbl["rows"][:6]:  # 처음 6행만 미리보기
            cells_str = "  |  ".join(
                f"[{c['row']},{c['cell']}] {c['text']}" for c in row
            )
            print(f"  │  {cells_str}")
        if len(tbl["rows"]) > 6:
            print(f"  │  ... ({len(tbl['rows'])-6}행 더 있음)")
        print(f"  └{'─'*60}")

    print(f"\n[단락 섹션 목록] — 총 {len(data['sections'])}개")
    for s in data["sections"]:
        mark = "🔵" if s["is_blue"] else "  "
        print(f"  {mark} {s['text']}")

    if data["blue_paragraphs"]:
        print(f"\n[파란 안내문구] — {len(data['blue_paragraphs'])}건 자동 삭제 대상")
        for b in data["blue_paragraphs"][:5]:
            print(f"  🔵 {b}")


def main():
    parser = argparse.ArgumentParser(description="DOCX 양식 구조 분석기")
    parser.add_argument("--docx", default="templates/datavoucher_2026.docx")
    parser.add_argument("--out",  default="docs/template_map.json")
    args = parser.parse_args()

    if not os.path.exists(args.docx):
        print(f"[오류] 파일을 찾을 수 없습니다: {args.docx}")
        print("  templates/ 폴더에 datavoucher_2026.docx를 넣고 다시 실행하세요.")
        return

    data = analyze(args.docx)
    print_report(data)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ template_map.json 저장 완료: {args.out}")
    print("   이 파일을 보고 render_agent.py의 TABLE_INDEX / SECTION_KEYWORD를 채우세요.")


if __name__ == "__main__":
    main()
