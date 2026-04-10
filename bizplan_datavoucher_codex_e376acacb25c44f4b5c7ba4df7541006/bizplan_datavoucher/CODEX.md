# bizplan_datavoucher — Codex 개발 가이드

> **목적**: 데이터바우처 사업수행계획서(DOCX)를 JSON 입력 데이터로부터 자동 생성하는 파이프라인.
> 이 파일은 Codex(AI 코딩 어시스턴트)가 프로젝트를 즉시 이해하고 이어서 개발할 수 있도록 작성된 단일 레퍼런스입니다.

---

## 1. 프로젝트 구조

```
bizplan_datavoucher/
├── orchestrator.py          ← 진입점. 5개 에이전트를 순서대로 호출
├── agents/
│   ├── writer_agent.py      ← 서술형 텍스트 → 개조식 변환
│   ├── table_agent.py       ← 사업비/일정/팀 데이터 구조화
│   ├── asset_agent.py       ← 이미지 경로·유효성 검증
│   ├── render_agent.py      ← DOCX 템플릿에 데이터 삽입 (핵심)
│   ├── docx_writer.py       ← python-docx 기반 실제 DOCX 조작 (가장 복잡)
│   ├── formatter.py         ← 볼드·밑줄 서식 자동화
│   ├── image_advisor.py     ← 이미지 슬롯 추천 및 위치 결정
│   └── qa_agent.py          ← 완성된 DOCX 검증
├── data/
│   ├── project_input.json   ← ★ 사용자가 편집하는 주 입력 파일
│   └── company_master.json  ← 기업 기본 정보 (고정)
├── templates/
│   └── datavoucher_2026.docx ← 원본 DOCX 양식 (수정 금지)
├── output/                  ← 생성 파일 저장
├── docs/
│   └── template_map.json    ← 템플릿 표 구조 분석 결과
└── schemas/
    └── master_schema.json   ← JSON 스키마 정의
```

---

## 2. 실행 방법

```bash
cd bizplan_datavoucher
python orchestrator.py
# 옵션:
# --master   data/company_master.json   (기본값)
# --project  data/project_input.json    (기본값)
# --template templates/datavoucher_2026.docx
# --output   output/사업계획서_완성.docx
```

**출력**: `output/사업계획서_완성.docx` + `output/사업계획서_완성_QA리포트.json`

---

## 3. 파이프라인 데이터 흐름

```
project_input.json
company_master.json
       │
       ▼
orchestrator.merge_content()
       │  content dict (모든 데이터 통합)
       ▼
WriterAgent.run(content)
  └─ narrative 텍스트 → 개조식 불릿으로 변환
  └─ content["narrative"][key] 값 in-place 수정
       │
       ▼
TableAgent.run(content)
  └─ budget_mix/budget_total → content["_tables"]["budget"]
  └─ schedule → 검증 및 정규화
  └─ team → content["_tables"]["team"]
       │
       ▼
AssetAgent.run(content)
  └─ assets 배열의 path 존재 여부 확인
  └─ content["_assets"] 에 유효 이미지 목록 저장
       │
       ▼
RenderAgent.run(content, template_path, output_path)
  └─ _build_injector_content(content) → injector_content dict 생성
  └─ _build_image_placeholders(content) → 이미지 슬롯 결정
  └─ docx_writer.write_docx() 호출 → DOCX 파일 생성
  └─ formatter.apply_formatting() → 볼드/밑줄 서식 적용
       │
       ▼
QAAgent.run(content, output_docx_path)
  └─ 누락 셀, 과락 조건, 이미지 규정 등 검사
  └─ output/사업계획서_완성_QA리포트.json 저장
```

---

## 4. 핵심 데이터 구조

### 4-1. `project_input.json` — 사용자 입력 파일

```jsonc
{
  "meta": {
    "program_name": "2026 데이터바우처 지원사업",
    "project_title": "과제명 (DOCX 표 [1,2]에 삽입)",
    "data_use_purpose": "운영효율화",          // 선택값: 서비스/제품 개발, 고도화, 운영효율화, 마케팅전략수립, 위험최소화, 고객예측
    "goal_100char": "100자 이내 사업목표"       // Ⅱ-2-가 섹션에 삽입
  },

  "narrative": {
    // ★ 각 키는 SECTION_KEYWORD 매핑을 통해 DOCX 특정 단락 뒤에 삽입됨
    "problem":           "가. 사업(과제) 목적 및 필요성 내용",
    "bm_intro":          "나. 비즈니스 모델 소개 내용",
    "differentiator":    "다. 비즈니스 모델의 특장점",
    "goal_100char":      // meta.goal_100char 사용 (중복 기재 불필요)
    "solution":          "나. 데이터 상품 및 활용 서비스 필요성",
    "budget_rationale":  "다. 사업비 편성 비중 (산출 근거)",
    "alliance_plan":     "가. 대외 제휴 계획",
    "pr_plan":           "나. 홍보계획",
    "expected_effect":   "가. 기대효과",
    "future_plan":       "나. 향후계획",
    "output_plan":       "가. 산출물 공개·활용 방안",
    "output_effect":     "나. 산출물 공개·활용 효과",
    "ceo_career":        // company_master.json의 ceo.career 사용
    "market_status":     // overview 표 [4,2]에도 삽입됨
  },

  "budget_mix": {        // 각 항목 비중 (합계 100)
    "planning":   0,     // 기획·설계
    "purchase":  20,     // 구매
    "collection": 0,     // 수집·생성
    "processing": 50,    // 가공
    "analysis":  30      // 분석
  },
  "budget_total": 30000000,  // 총 사업비 (원)

  "schedule": [          // 추진일정 표 (최대 18행)
    {
      "task":    "세부 업무명",
      "m1": true, "m2": true, "m3": false, "m4": false, "m5": false, "m6": false,
      "weight":  25,     // 비중 (%)
      "content": "수행내용 + 완료 기준"
    }
  ],

  "team": [              // 참여인력 (표 #10, 최대 6명)
    {
      "name": "홍길동",
      "title": "과장",
      "role": "주요 담당업무",
      "career": "경력 및 학력",
      "hire_date": "'24.1",   // 또는 "신규"
      "participation": 50,    // 참여율 (%)
      "is_new_hire": false
    }
  ],

  "hire_plan": [         // 추가 고용계획 (표 #11, 최대 5행)
    {
      "role":   "서비스 개발",
      "skills": "요구 경력·학력",
      "hire_month": "M+2"    // 채용 시기
    }
  ],

  "assets": [            // 이미지 슬롯 (slot_id는 아래 이미지 슬롯 참조)
    {
      "slot_id": "SLOT_OVERVIEW_IMG",
      "title":   "이미지 제목",
      "path":    "generated_images/image.png"
    }
  ]
}
```

### 4-2. `company_master.json` — 기업 고정 정보

```jsonc
{
  "company": {
    "name": "기업명",
    "biz_no": "000-00-00000",
    "founded": "2020-01",
    "address": "서울시 ...",
    "industry": "소프트웨어 개발",
    "employee_count": 5,
    "annual_revenue": 100000000
  },
  "ceo": {
    "name": "대표자명",
    "career": ["경력1", "경력2", "경력3"]
  },
  "core_competency": ["핵심역량1", "핵심역량2"]
}
```

---

## 5. DOCX 템플릿 표 인덱스 (TABLE_INDEX)

`render_agent.py`에 정의된 상수. 원본 DOCX에서 작성요령 표 20개가 삭제된 후의 실제 인덱스.

```python
TABLE_INDEX = {
    "overview":   3,   # 수요기업 개요표 (Ⅰ장) — 8행 4열
    "budget":     5,   # 사업비 편성 비중 — 3행 7열
    "schedule":   7,   # 추진일정 — 20행 10열
    "staff_cnt":  9,   # 재직/고용 인원수 — 1행 4열
    "team":      10,   # 참여인력 현황 — 최대 7행 7열
    "hire_plan": 11,   # 추가 인력 고용계획 — 최대 6행 4열
}
```

**overview 표 셀 매핑** (row, cell):

| row | cell 2 내용 |
|-----|------------|
| 1   | 과제명 |
| 2   | 사업 개요 요약 (활용목적 + 100자 목표) |
| 3   | 핵심역량 |
| 4   | 국내외 시장현황 (market_status) |
| 5   | 데이터 상품 및 활용서비스 필요성 (solution) |
| 6~7 | 관련 이미지 (SLOT_OVERVIEW_IMG) |

---

## 6. SECTION_KEYWORD — 섹션 단락 삽입 매핑

`render_agent.py`에 정의. 단락 헤딩 텍스트를 키워드로 찾아 그 **직후에** 텍스트를 삽입.

```python
SECTION_KEYWORD = {
    "problem":          "가. 사업(과제) 목적 및 필요성",
    "bm_intro":         "나. 비즈니스 모델 소개",
    "differentiator":   "다. 비즈니스 모델의 특장점",
    "goal_100char":     "가. 데이터를 활용한 사업(창업)목표",
    "solution":         "나. 데이터 상품 및 활용 서비스 필요성",
    "budget_rationale": "다. 사업비 편성 비중",        # ← 신규 추가
    "alliance_plan":    "가. 대외 제휴 계획",
    "pr_plan":          "나. 홍보계획(예비창업자의 경우 자금소요 및 조달 계획 작성)",
    "expected_effect":  "가. 기대효과",
    "future_plan":      "나. 향후계획",
    "output_plan":      "가. 산출물 공개·활용 방안",
    "output_effect":    "나. 산출물 공개·활용 효과",
    "ceo_career":       "가. 대표자 역량",
}
```

> ⚠️ 섹션 키워드는 DOCX 원본 단락 텍스트와 **완전 일치**해야 합니다.
> 새 섹션을 추가하려면: ① `narrative` 키 추가 → ② `SECTION_KEYWORD` 등록 → ③ `project_input.json` 값 추가

---

## 7. docx_writer.py — 핵심 함수 목록

가장 복잡한 파일. 1082줄. 주요 함수:

```python
# ── 진입점 ──────────────────────────────────────────────────────
write_docx(template_path, output_path, injector_content) -> dict
  """
  반환값:
    cells_written, sections_written, images_inserted, images_placeholder,
    blank_tables_inserted, empty_rows_removed, tables_deleted,
    paras_deleted, blue_rows_deleted, blank_removed
  """
  # 실행 순서:
  # STEP 1   셀 채우기     (_set_cell_text)
  # STEP 1-B 잉여 빈 행 정리 (trim_table_empty_rows)
  # STEP 1-C 실제 이미지 삽입 (insert_image_in_cell, insert_image_after_para)
  # STEP 2   섹션 텍스트 삽입 (_insert_text_after_para)
  # STEP 2-B 이미지 placeholder 삽입
  # STEP 2-C 빈 칸 표 삽입
  # STEP 3   작성요령 삭제 (delete_guide_elements)
  # STEP 4   연속 공백 압축 (collapse_blank_paras)

# ── 셀 조작 ─────────────────────────────────────────────────────
_set_cell_text(tc_elem, text)         # 셀 텍스트 설정 + 색상/이탤릭 초기화
_clear_cell(tc_elem)                  # 셀 내용 전체 삭제
trim_table_empty_rows(doc, table_idx, data_start_row)  # 빈 행 제거

# ── 단락 조작 ────────────────────────────────────────────────────
_insert_text_after_para(doc, keyword, lines)  # 키워드 단락 뒤에 텍스트 삽입
_write_para(parent_elem, text, ref_para_elem) # 단락 생성 (색상·이탤릭 초기화)

# ── 이미지 삽입 ──────────────────────────────────────────────────
insert_image_in_cell(doc, table_idx, row, cell, image_path, width_cm, height_cm)
insert_image_after_para(doc, keyword, image_path, title, width_cm, height_cm, offset)
_get_image_drawing_xml(doc, image_path, width_cm, height_cm) -> etree._Element

# ── 빈 칸 표 (이미지 placeholder) ────────────────────────────────
insert_blank_image_table_after_para(doc, keyword, title, height_cm, offset)
_make_blank_image_table(doc, title, height_cm) -> Table

# ── 삭제 로직 ────────────────────────────────────────────────────
delete_guide_elements(doc)
  # - <작성요령> 텍스트가 있는 표 전체 삭제 (_tbl_is_guide)
  # - _KEEP_TABLES 내 파란 이탤릭 안내 행 삭제
  # - 파란색·이탤릭 서식 강제 초기화 (흰색 ffffff는 보존)
_tbl_is_guide(tbl) -> bool           # "< 작성요령 >" 텍스트 포함 여부

# ── 공백 처리 ────────────────────────────────────────────────────
collapse_blank_paras(doc, max_blank=1)  # 연속 빈 단락 압축
_compress(paras, max_blank)             # 셀/본문 공통 압축 로직

# ── 색상 정책 ────────────────────────────────────────────────────
_PRESERVE_COLORS = {"ffffff", ...}   # 이 색상은 초기화하지 않음
_should_reset_color(val) -> bool     # True면 000000으로 초기화
```

---

## 8. render_agent.py — 핵심 구조

```python
class RenderAgent:
    def run(content, template_path, output_path) -> stats
        # INJECTOR_AVAILABLE=False → _direct_write() 호출

    def _direct_write(content, template_path, output_path) -> stats
        # 1. _build_injector_content(content) → injector_content
        # 2. _build_image_placeholders(content) → image_placeholders
        # 3. docx_writer.write_docx() 호출
        # 4. formatter.apply_formatting() 호출
        # 5. stats 반환

    def _build_injector_content(content) -> dict
        # injector_content 구조:
        # {
        #   "cells":             [{"table":int, "row":int, "cell":int, "text":str}, ...],
        #   "sections":          [{"keyword":str, "text":str}, ...],
        #   "image_slots":       {"SLOT_ID": {"path":str, "table_index":int, ...}},
        #   "image_placeholders":{"SLOT_ID": {"location":str, "caption_text":str, ...}},
        #   "blank_image_slots": [{"para_keyword":str, "title":str, "height_cm":float}, ...],
        #   "trim_tables":       [{"table_index":int, "data_start_row":int}, ...],
        # }
```

---

## 9. 이미지 슬롯 시스템

`image_advisor.py`에 정의된 5개 슬롯.

| slot_id | 위치 | 우선순위 | 이미지 종류 |
|---------|------|---------|------------|
| `SLOT_OVERVIEW_IMG` | overview 표 [6,2] (표 셀) | 1-필수 | 서비스 구조도 |
| `SLOT_BM_FLOW` | '나. 비즈니스 모델 소개' 단락 뒤 | 2-권장 | BM 다이어그램 |
| `SLOT_TECH_ARCH` | '나. 데이터 상품 및 활용 서비스 필요성' 단락 뒤 | 2-권장 | 기술 아키텍처 |
| `SLOT_EXPECTED_KPI` | '가. 기대효과' 단락 뒤 | 2-권장 | KPI 인포그래픽 |
| `SLOT_MARKET_CHART` | '1. 사업(과제) 개요' 단락 뒤 | 3-선택 | 시장 규모 차트 |

**이미지 분기 로직** (`image_advisor.py` → `run()` 메서드):
- `assets`에 `slot_id`와 `path`가 있고 파일이 존재 → `image_slots` (실제 삽입)
- 파일 없음 → `image_placeholders` + `blank_image_slots` (텍스트 안내 + 빈 칸 표)

---

## 10. WriterAgent — 개조식 변환 로직

```python
# 3단계 파이프라인
def to_bullet(text) -> str:
    sentences = _split_into_sentences(text)   # 마침표 기준 문장 분리
    return "\n".join(f"· {_convert_ending(s)}" for s in sentences if s.strip())

def _split_into_sentences(text) -> list[str]:
    # 1. 쉼표 복합절 분리 (하고,/하며,/하여,)
    # 2. 마침표 기준 분리
    # 3. 빈 줄 기준 분리

def _convert_ending(sentence) -> str:
    # STAGE 1: 복합 종결어미 전처리 (조동사/상태/연결어미)
    # STAGE 2: _ENDING_REPLACE_V5 패턴 적용 → 명사형 변환
    # STAGE 3: _POST_CLEANUP 후처리 (조사 제거: 을/를/도)
```

`bullet_convert=True` (기본값)이면 모든 `narrative` 텍스트에 자동 적용.

> ⚠️ `budget_rationale` 등 구조화된 텍스트는 `BULLET_SKIP_FIELDS`에 추가하면 변환 건너뜀.

---

## 11. formatter.py — 서식 자동화

```python
apply_formatting(doc_path) -> {"title_bolded": int}
  # - ①②③+콜론 패턴 → 콜론까지 볼드
  # - 가나다 헤딩 패턴 → 전체 볼드
  # - 글머리 기호(·, •, ▶) → 볼드 제외

apply_underline(doc_path) -> {"underline_runs": int}
  # - 수치+단위 패턴 (87%, 2.3조 원, 18%p 등) → 밑줄
  # - 핵심 키워드 구문 → 밑줄
```

---

## 12. 알려진 제약사항 및 TODO

### 현재 제약
- `budget_total`, `budget_mix`는 `project_input.json`에 직접 수기 입력 필요
- `budget_rationale` 텍스트에 `○○○`(공란) 포함 — 실제 견적 수령 후 교체 필요
- 이미지 4장 동시 삽입 시 QA 경고 발생 (데이터바우처 규정: 표지 이미지 1장)
- `WriterAgent`의 `bullet_convert`가 `budget_rationale` 같은 구조화 텍스트도 변환함

### 다음 개발 과제 (우선순위 순)

#### 🔴 HIGH
1. **`budget_total` 자동 계산**: `budget_mix`의 비율과 단가를 입력받아 `budget_total` 자동 산출
2. **`bullet_convert` 제외 필드 목록**: `BULLET_SKIP_FIELDS = ["budget_rationale", "solution"]` 등 구조화 텍스트는 변환 제외
3. **○○○ 공란 검출 QA 항목 추가**: `qa_agent.py`에서 DOCX 내 `○○○` 텍스트 잔존 시 경고 발생

#### 🟡 MEDIUM
4. **다중 양식 지원**: `template_path`를 환경변수로 분리하여 AI바우처·글로벌성장바우처 등 다른 양식 지원
5. **`project_input.json` 유효성 검사**: 필수 키 누락, 배점 합계 100% 초과 등 사전 검증
6. **LLM 자동 문안 생성** (`--llm` 플래그): `WriterAgent`의 `llm_enabled=True` 경로 구현
7. **스케줄 비중 합계 검증**: `schedule[].weight` 합이 100이 아닐 경우 경고

#### 🟢 LOW
8. **CLI 인수 개선**: `--dry-run` 플래그로 DOCX 생성 없이 QA 미리보기
9. **테스트 커버리지 추가**: `writer_agent.py` 27개 케이스 외 `docx_writer.py` 단위 테스트

---

## 13. 환경 설정

```bash
pip install python-docx lxml
# (선택) LLM 활성화 시
pip install openai
```

Python 3.9+ 필요. 외부 API 의존성 없음 (LLM 비활성 시).

---

## 14. 자주 묻는 개발 질문

**Q. 새 섹션을 추가하려면?**
```
1. project_input.json → narrative 에 키 추가
2. render_agent.py → SECTION_KEYWORD 에 {키: "단락 헤딩 텍스트"} 추가
3. 헤딩 텍스트는 DOCX 원본 단락과 완전히 일치해야 함
```

**Q. 표 인덱스가 왜 맞지 않나요?**
```
delete_guide_elements()가 <작성요령> 표를 삭제하기 때문에
TABLE_INDEX는 삭제 후 기준 인덱스입니다.
원본 템플릿의 실제 표 인덱스는 docs/template_map.json 참조.
```

**Q. 이미지가 삽입되지 않을 때?**
```
1. assets[].path 파일 존재 여부 확인
2. SLOT_OVERVIEW_IMG는 표 셀 삽입 (insert_image_in_cell)
3. 나머지 슬롯은 단락 뒤 삽입 (insert_image_after_para)
4. image_slots와 image_placeholders 중복 등록 여부 확인
   (render_agent._build_image_placeholders 내 image_slot_ids 제외 로직)
```

**Q. 색상이 잘못 바뀔 때?**
```
_should_reset_color()의 _PRESERVE_COLORS 집합 확인.
흰색(ffffff) 텍스트는 보존, 파란색(0000ff/0070c0) 등은 000000으로 초기화.
```

**Q. 개조식 변환이 이상할 때?**
```
writer_agent.py의 _ENDING_REPLACE_V5, _POST_CLEANUP 패턴 확인.
해당 텍스트가 _split_into_sentences()로 올바르게 분리되는지 먼저 확인.
변환을 건너뛰려면 해당 키를 BULLET_SKIP_FIELDS에 추가.
```
