# bizplan_datavoucher
**데이터바우처 사업계획서 자동작성 엔진 — MVP v1.0**

> 분업은 맞고, 분산은 나중입니다.  
> 한 프로젝트 안에서 5개 에이전트가 역할을 나눠 처리합니다.

---

## 프로젝트 구조

```
bizplan_datavoucher/
├── orchestrator.py          ← ★ 실행 진입점 (총괄 오케스트레이터)
│
├── agents/
│   ├── writer_agent.py      ← 서술형 섹션 문안 생성
│   ├── table_agent.py       ← 사업비/일정/인력 표 구조화 + 수치 검증
│   ├── asset_agent.py       ← 이미지 경로·제목 정리
│   ├── render_agent.py      ← DOCX 실제 삽입 (BizPlanInjector 호출)
│   └── qa_agent.py          ← 누락·불일치·제약 위반 최종 검사
│
├── schemas/
│   └── master_schema.json   ← 3계층 데이터 구조 정의서
│
├── templates/
│   └── datavoucher_2026.docx  ← ★ 원본 양식 (직접 넣어야 함)
│
├── data/
│   ├── company_master.json  ← 기업 공통 정보 (한 번 입력 후 재사용)
│   └── project_input.json   ← 과제별 입력 데이터
│
├── output/                  ← 생성된 DOCX 파일 저장 위치
├── prompts/                 ← Phase 3 LLM 프롬프트 템플릿
└── docs/                    ← 설계문서 저장 위치
```

---

## 빠른 시작

### 1. 의존성 설치
```bash
pip install lxml python-docx
```

### 2. 원본 양식 넣기
`templates/datavoucher_2026.docx` 위치에 실제 데이터바우처 양식 파일을 복사합니다.

### 3. 기업 정보 입력
`data/company_master.json`을 열어 회사명, 대표자, 핵심역량을 수정합니다.

### 4. 과제 정보 입력
`data/project_input.json`을 열어 과제명, 서술 내용, 사업비, 일정, 인력을 입력합니다.

### 5. 실행
```bash
python orchestrator.py
```

또는 경로 직접 지정:
```bash
python orchestrator.py \
  --master  data/company_master.json \
  --project data/project_input.json \
  --template templates/datavoucher_2026.docx \
  --output  output/사업계획서_완성.docx
```

---

## 5개 에이전트 역할 분리

| 에이전트 | 담당 | 건드리는 것 |
|---------|------|------------|
| **WriterAgent** | 서술형 문안 생성 | narrative 섹션 (problem/solution/market 등) |
| **TableAgent** | 표 데이터 구조화 + 수치 검증 | budget_mix / schedule / team |
| **AssetAgent** | 이미지 정리 | assets (최대 1장 제한 적용) |
| **RenderAgent** | DOCX 실제 삽입 | ★ DOCX에 손대는 유일한 에이전트 |
| **QAAgent** | 최종 검사 | 모든 content를 읽기만 함 (수정 안 함) |

---

## QA 검사 항목

### 필수 오류 (통과 실패 시 exit code 1)
| 코드 | 내용 |
|-----|------|
| E01 | 과제명에 '데이터' 관련 단어 미포함 |
| E02 | 구매/가공 비중 모두 0% (최소 1개 > 0% 필수) |
| E03 | 사업비 비중 합계 ≠ 100% |
| E04 | 개인정보 활용 과제인데 개인정보보호관리자 미지정 |
| E05 | 수행인력 미입력 |
| E06 | 핵심 서술 섹션(문제인식/실현방안/시장현황) 비어 있음 |

### 경고 (수정 권고)
| 코드 | 내용 |
|-----|------|
| W01 | 데이터 활용 목표 100자 초과 |
| W02 | 단일 사업비 항목 70% 초과 |
| W03 | 추진일정 비중 합계 ≠ 100% |
| W04 | 수행인력 참여율 권고 범위 이탈 |
| W05 | 이미지 파일 없어 삽입 건너뜀 |
| W06 | 과제명 50자 초과 |
| W07 | 기대효과 항목 비어 있음 |

---

## 3계층 데이터 구조

| 계층 | 파일 | 변경 빈도 | 설명 |
|-----|------|---------|------|
| **Master** | `company_master.json` | 낮음 | 기업명·대표자·핵심역량 등 공통 정보 |
| **Project** | `project_input.json` | 중간 | 과제명·서술·사업비·일정·인력 |
| **Program** | `schemas/master_schema.json` > program | 높음 | 공모별 제약 규칙 |

---

## 개발 단계 로드맵

| 단계 | 기간 | 내용 |
|-----|------|------|
| **Phase 1 (MVP)** ← 지금 여기 | 1~3주 | DOCX 1종, JSON 입력, 표 2종, QA 리포트 출력 |
| **Phase 2 (확장)** | 4~6주 | 평가항목 자동 매핑, 기업 DB, 양식 2종 이상 |
| **Phase 3 (고도화)** | 7~8주 | LLM 문안 생성 (`--llm` 플래그 활성화), 문체 프리셋 |

---

## 주의사항

1. **글 쓰는 에이전트(WriterAgent)가 표 구조를 직접 건드리면 안 됩니다.**
2. **표 채우는 에이전트(TableAgent)가 사업 논리를 바꾸면 안 됩니다.**
3. **렌더링은 RenderAgent 하나에서만 합니다.**
4. **QA는 반드시 마지막 관문입니다.** 오류가 있으면 수정 후 재실행하세요.

---

## 성공 판정 기준

- ✅ 새 프로젝트에서 30분 내 초안 생성 가능
- ✅ 기존 마스터 데이터 재사용률 70% 이상
- ✅ QA 오류 0건으로 출력 DOCX 생성
- ✅ 비개발자가 개발자 도움 없이 혼자 돌릴 수 있음
