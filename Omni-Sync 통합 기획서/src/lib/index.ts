export const ROUTE_PATHS = { HOME: '/' } as const;

// ─── 타입 정의 ────────────────────────────────────────────────
export interface Feature {
  id: string;
  title: string;
  description: string;
  subFeatures: string[];
  advantage: string;           // 핵심 장점 (Omni-Sync 병합)
  priority: 'P0' | 'P1' | 'P2';
  complexity: '낮음' | '중간' | '높음' | '매우높음';
  phase: 1 | 2 | 3;
  techTags: string[];           // 기술 스택 태그
}

export interface Category {
  id: string;
  icon: string;
  title: string;
  subtitle: string;
  color: string;
  domain: 'work' | 'file' | 'life' | 'finance' | 'shopping' | 'dev';
  features: Feature[];
}

export interface ArchLayer {
  id: string;
  title: string;
  subtitle: string;
  tech: string[];
  desc: string;
  color: string;
}

export interface Domain {
  id: 'work' | 'file' | 'life' | 'finance' | 'shopping' | 'dev';
  icon: string;
  title: string;
  titleEn: string;
  color: string;
  useCase: string;
  techTerms: string[];
}

export interface TimelinePhase {
  phase: number;
  title: string;
  duration: string;
  description: string;
  todos: string[];
}

// ─── 서비스 아이덴티티 ────────────────────────────────────────
export const SERVICE_NAME    = 'Omni-Sync';
export const SERVICE_FULL    = '초개인화 통합 AI 에이전트';
export const SERVICE_TAGLINE = "'Zero-Click' 환경 구축 — 인지(LLM/Vision)와 실행(RPA/API)을 결합한 자율형 AI 비서";
export const SERVICE_VERSION = 'v0.2 통합 기획안';
export const CORE_VALUE      = 'Zero-Click';
export const ARCH_STACK      = 'React · FastAPI · Docker (Microservices)';

// ─── 시스템 아키텍처 레이어 ───────────────────────────────────
export const ARCH_LAYERS: ArchLayer[] = [
  {
    id: 'interface',
    title: 'Interface Layer',
    subtitle: 'React 프론트엔드',
    tech: ['React', 'TypeScript', 'Tailwind CSS', 'shadcn/ui'],
    desc: '사용자가 필터 조건을 콤보박스로 설정하거나 프롬프트(음성·텍스트)를 입력하는 직관적인 대시보드. 각 자동화 모듈 상태를 실시간으로 모니터링.',
    color: 'from-blue-500/20 to-cyan-500/10',
  },
  {
    id: 'api',
    title: 'API & Logic Layer',
    subtitle: 'FastAPI 비동기 백엔드',
    tech: ['FastAPI', 'Python', 'Async/Await', 'LLM Orchestration'],
    desc: '비동기 처리에 강한 FastAPI로 LLM 추론·웹 크롤링 작업을 병렬 처리. Event-driven Architecture 기반으로 수신 이벤트마다 자동 파이프라인 트리거.',
    color: 'from-violet-500/20 to-purple-500/10',
  },
  {
    id: 'execution',
    title: 'Data & Execution Layer',
    subtitle: 'RPA / AI Agents',
    tech: ['RPA Engine', 'Local Agent', 'OCR/Vision AI', 'LLM Parser'],
    desc: 'OS 제어(파일 이동·데스크톱 트래킹)를 위한 로컬 Agent와 클라우드 DB 연동. Vision AI·OCR이 비정형 데이터(이미지·PDF)를 구조화 데이터로 변환.',
    color: 'from-emerald-500/20 to-green-500/10',
  },
  {
    id: 'infra',
    title: 'Infrastructure',
    subtitle: 'Docker 마이크로서비스',
    tech: ['Docker', 'Container Isolation', 'Cron Scheduler', 'Message Queue'],
    desc: '수집(Scraping)·인지(OCR/LLM)·실행(RPA) 모듈을 각각의 Docker 컨테이너로 분리. 특정 서비스 오류가 전체 시스템에 영향을 주지 않도록 격리(Isolation).',
    color: 'from-amber-500/20 to-orange-500/10',
  },
];

// ─── 5대 핵심 도메인 ──────────────────────────────────────────
export const DOMAINS: Domain[] = [
  {
    id: 'work',
    icon: '💼',
    title: '업무 자동화',
    titleEn: 'Work',
    color: 'border-blue-500/40 bg-blue-500/5',
    useCase: '컨설턴트 신청 메일 수신 시 LLM이 내용 파싱 → 지정 폴더 생성 → 신청서 다운로드 → 가안 작성 후 임시저장 상태로 승인 대기.',
    techTerms: ['LLM Parsing', 'RPA', 'Event-driven Architecture', 'Webhook'],
  },
  {
    id: 'file',
    icon: '🗂️',
    title: '파일 & 데이터',
    titleEn: 'File & Data',
    color: 'border-purple-500/40 bg-purple-500/5',
    useCase: '와인 사진 분류 시 Vision AI가 객체 인식 후 메타데이터(날짜·레드/화이트·가격대)를 태깅하여 폴더 이동 및 파일명 자동 변경(Rename).',
    techTerms: ['OCR & Vision AI', 'SHA-256', 'Dynamic Web Scraping', 'Entity Extraction'],
  },
  {
    id: 'life',
    icon: '🌅',
    title: '생활 밀착형',
    titleEn: 'Life',
    color: 'border-emerald-500/40 bg-emerald-500/5',
    useCase: '스마트 스토리지: 집안 소모품 중량·수량 기반 재고 부족 시점 예측 및 자동 발주. 아침 기상 시 날씨·일정·뉴스·약 복용 알림 TTS 송출.',
    techTerms: ['IoT Data Ingestion', 'TTS/STT', 'Predictive Analytics', 'Calendar API'],
  },
  {
    id: 'finance',
    icon: '📈',
    title: '금융 & 투자',
    titleEn: 'Finance & Invest',
    color: 'border-amber-500/40 bg-amber-500/5',
    useCase: '포트폴리오 오토 파일럿: 주식·코인·안전자산 지표 모니터링 및 목표 수익률·예산에 따른 매매 타이밍·수량 추천 및 자동 매수/매도(Algo-Trading).',
    techTerms: ['MyData API', 'Open API', 'Time-series Analysis', 'Slippage Control'],
  },
  {
    id: 'shopping',
    icon: '🛒',
    title: '쇼핑 에이전트',
    titleEn: 'Shopping',
    color: 'border-rose-500/40 bg-rose-500/5',
    useCase: '쇼핑 스니핑: 생필품 웹 최저가를 주기적으로 크롤링(Cronjob)하여 변동 추이 분석 후 최적 타이밍에 자동 결제 승인 요청.',
    techTerms: ['Web Crawler', 'Cron Scheduler', 'Price Tracking', 'Auto-purchase'],
  },
  {
    id: 'dev',
    icon: '⚙️',
    title: '개발 자동화',
    titleEn: 'Dev Automation',
    color: 'border-fuchsia-500/40 bg-fuchsia-500/5',
    useCase: '목표(Goal) 텍스트 입력 시 AI가 태스크 분해 → 코드 생성 → 테스트 → 오류 수정 루프를 24/7 자율 반복. 마일스톤마다 사용자 승인 게이트.',
    techTerms: ['LLM Code Gen', 'CI/CD', 'Multi-Agent', 'Auto-Test'],
  },
];

// ─── 개발 로드맵 ──────────────────────────────────────────────
export const TIMELINE_PHASES: TimelinePhase[] = [
  {
    phase: 1,
    title: 'MVP — 데이터 수집 & 업무 자동화',
    duration: '1~2개월',
    description: '핵심 파이프라인 구축. 빠른 가치 검증.',
    todos: [
      'FastAPI 기반 백엔드 프로젝트 세팅 및 Docker 환경 구성',
      '이메일 수신 Webhook 연동 및 LLM 기반 파싱 로직 개발',
      '로컬 스토리지 중복 파일(SHA-256 해시) 제거 스크립트',
      '사진 OCR 메타 태깅 및 자동 분류 모듈 작성',
      'React 대시보드 UI 프로토타이핑 (크롤링 필터 설정 포함)',
      '캘린더 API 연동 및 음성/텍스트 기반 일정 자동 등록',
    ],
  },
  {
    phase: 2,
    title: 'Intelligence — 생활 & 루틴 자동화 확장',
    duration: '3~4개월',
    description: '일상 전반 AI 루틴화. 생활 밀착 기능 완성.',
    todos: [
      '기상/취침 브리핑 (날씨·뉴스·준비물 체크리스트) 로직 구현',
      '멀티 명함 이미지 Crop → OCR → 연락처 API 동기화',
      '점심·저녁 메뉴 추천 엔진 (주문 내역 기반 학습)',
      '쇼핑몰 웹 크롤러 스케줄링 및 최저가 알림 구현',
      '마이데이터 API 연동 — 카드 실적 트래킹',
      '목표 기반 자율 개발 에이전트 프로토타입 구축',
    ],
  },
  {
    phase: 3,
    title: 'Autonomy — 외부 연동 고도화 & 자율 실행',
    duration: '5개월~',
    description: '완전 자율 시스템. 외부 API·IoT·알고트레이딩 통합.',
    todos: [
      '증권사 API 연동 — 관심 종목 지표 수집·알림·자동 매매',
      '스마트홈 센서 데이터 수집 파이프라인 (가스·전기·수도)',
      '메일 내용 → 할 일 자동 생성 → 자율 실행 → 결과 보고',
      '멀티 에이전트 병렬 개발 시스템 고도화',
      '전체 서비스 모니터링 대시보드 완성',
      '정기 구매 자동 주문 (최저가 쇼핑몰 자동 결제)',
    ],
  },
];
