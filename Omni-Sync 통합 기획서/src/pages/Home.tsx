import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { springPresets, staggerContainer, staggerItem } from '@/lib/motion';
import { CATEGORIES } from '@/data/categories';
import {
  ARCH_LAYERS, DOMAINS, TIMELINE_PHASES,
  SERVICE_NAME, SERVICE_FULL, SERVICE_TAGLINE, SERVICE_VERSION,
  CORE_VALUE, ARCH_STACK,
} from '@/lib/index';
import type { Category, Feature } from '@/lib/index';
import {
  Sun, Calendar, CheckSquare, MessageSquare, Utensils, Mail,
  Megaphone, CreditCard, TrendingUp, ShoppingCart, Home as HomeIcon,
  FolderOpen, BarChart2, Moon, ChevronDown, ChevronUp,
  Layers, Zap, Target, Clock, Code2, Server, Database, Cpu, Globe,
  Sparkles, ArrowRight,
} from 'lucide-react';

// ─── 아이콘 매핑 ──────────────────────────────────────────────
const ICON_MAP: Record<string, React.ReactNode> = {
  morning: <Sun className="w-5 h-5" />,
  schedule: <Calendar className="w-5 h-5" />,
  task: <CheckSquare className="w-5 h-5" />,
  communication: <MessageSquare className="w-5 h-5" />,
  meal: <Utensils className="w-5 h-5" />,
  'mail-auto': <Mail className="w-5 h-5" />,
  announcement: <Megaphone className="w-5 h-5" />,
  finance: <CreditCard className="w-5 h-5" />,
  investment: <TrendingUp className="w-5 h-5" />,
  shopping: <ShoppingCart className="w-5 h-5" />,
  home: <HomeIcon className="w-5 h-5" />,
  file: <FolderOpen className="w-5 h-5" />,
  tracking: <BarChart2 className="w-5 h-5" />,
  night: <Moon className="w-5 h-5" />,
  'dev-auto': <Code2 className="w-5 h-5" />,
};

const ARCH_ICON: Record<string, React.ReactNode> = {
  interface: <Globe className="w-5 h-5" />,
  api: <Server className="w-5 h-5" />,
  execution: <Cpu className="w-5 h-5" />,
  infra: <Database className="w-5 h-5" />,
};

const PRIORITY_STYLE: Record<string, string> = {
  P0: 'bg-red-500/15 text-red-400 border border-red-500/30',
  P1: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
  P2: 'bg-slate-500/15 text-slate-400 border border-slate-500/30',
};
const PRIORITY_LABEL: Record<string, string> = { P0: '핵심', P1: '중요', P2: '개선' };

const COMPLEXITY_STYLE: Record<string, string> = {
  '낮음': 'text-emerald-400', '중간': 'text-cyan-400',
  '높음': 'text-amber-400', '매우높음': 'text-rose-400',
};

const PHASE_COLOR: Record<number, string> = {
  1: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
  2: 'bg-violet-500/20 text-violet-300 border border-violet-500/30',
  3: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
};

// ─── 기능 카드 ──────────────────────────────────────────────
function FeatureCard({ feature }: { feature: Feature }) {
  const [open, setOpen] = useState(false);
  return (
    <motion.div layout className="rounded-xl border border-border bg-card/60 overflow-hidden"
      style={{ boxShadow: '0 2px 12px -4px rgba(0,0,0,0.3)' }}>
      <button className="w-full text-left p-4 flex items-start gap-3 hover:bg-muted/30 transition-colors"
        onClick={() => setOpen(!open)}>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            <span className={`text-xs px-2 py-0.5 rounded-full font-mono font-medium ${PRIORITY_STYLE[feature.priority]}`}>
              {PRIORITY_LABEL[feature.priority]}
            </span>
            <span className={`text-xs font-mono font-medium ${PHASE_COLOR[feature.phase]} px-2 py-0.5 rounded-full`}>
              Phase {feature.phase}
            </span>
            <span className={`text-xs font-medium ${COMPLEXITY_STYLE[feature.complexity]}`}>
              복잡도: {feature.complexity}
            </span>
          </div>
          <h4 className="font-semibold text-foreground text-sm leading-snug">{feature.title}</h4>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{feature.description}</p>
          {/* 장점 하이라이트 */}
          <div className="mt-2 flex items-start gap-1.5">
            <Sparkles className="w-3 h-3 text-accent mt-0.5 flex-shrink-0" />
            <p className="text-xs text-accent/90 leading-relaxed">{feature.advantage}</p>
          </div>
          {/* 기술 태그 */}
          <div className="mt-2 flex flex-wrap gap-1">
            {feature.techTags.map(tag => (
              <span key={tag} className="text-xs bg-primary/10 text-primary/80 border border-primary/20 px-1.5 py-0.5 rounded font-mono">
                {tag}
              </span>
            ))}
          </div>
        </div>
        <div className="text-muted-foreground mt-0.5 flex-shrink-0">
          {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden">
            <div className="px-4 pb-4 pt-0 border-t border-border/60">
              <p className="text-xs text-muted-foreground mb-2 mt-3 font-medium uppercase tracking-wide">세부 기능</p>
              <ul className="space-y-1.5">
                {feature.subFeatures.map((sf, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-foreground/80">
                    <span className="text-primary mt-0.5 flex-shrink-0">▸</span>
                    <span>{sf}</span>
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ─── 카테고리 섹션 ──────────────────────────────────────────
function CategorySection({ cat, index }: { cat: Category; index: number }) {
  return (
    <motion.section variants={staggerItem} id={cat.id}
      className="rounded-2xl border border-border overflow-hidden"
      style={{ boxShadow: '0 4px 24px -8px rgba(0,0,0,0.4)' }}>
      <div className={`bg-gradient-to-r ${cat.color} p-5 border-b border-border/60`}>
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-background/40 border border-border/60 flex items-center justify-center text-foreground">
              {ICON_MAP[cat.id]}
            </div>
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-xs text-muted-foreground font-mono">#{String(index + 1).padStart(2, '0')}</span>
              </div>
              <h3 className="font-bold text-foreground text-base leading-tight">{cat.title}</h3>
              <p className="text-xs text-muted-foreground mt-0.5">{cat.subtitle}</p>
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <div className="text-2xl font-bold font-mono text-foreground">{cat.features.length}</div>
            <div className="text-xs text-muted-foreground">기능</div>
          </div>
        </div>
      </div>
      <div className="p-4 bg-background/40 space-y-3">
        {cat.features.map(feature => (
          <FeatureCard key={feature.id} feature={feature} />
        ))}
      </div>
    </motion.section>
  );
}

// ─── 아키텍처 섹션 ──────────────────────────────────────────
function ArchSection() {
  return (
    <section id="architecture" className="mb-12">
      <h2 className="text-xl font-bold text-foreground mb-1 flex items-center gap-2">
        <Server className="w-5 h-5 text-primary" />
        시스템 아키텍처
      </h2>
      <p className="text-sm text-muted-foreground mb-6">
        비동기(Async) 마이크로서비스 설계 — 각 모듈 독립 배포 및 장애 격리(Isolation)
      </p>
      <div className="space-y-3">
        {ARCH_LAYERS.map((layer, i) => (
          <motion.div key={layer.id} variants={staggerItem}
            className="rounded-2xl border border-border overflow-hidden"
            style={{ boxShadow: '0 2px 12px -4px rgba(0,0,0,0.3)' }}>
            <div className={`bg-gradient-to-r ${layer.color} p-4 flex items-start gap-4`}>
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-background/40 border border-border/60 flex items-center justify-center text-foreground flex-shrink-0">
                  {ARCH_ICON[layer.id]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-mono text-muted-foreground">Layer {i + 1}</span>
                  </div>
                  <h3 className="font-bold text-foreground text-sm">{layer.title}</h3>
                  <p className="text-xs text-muted-foreground">{layer.subtitle}</p>
                </div>
              </div>
            </div>
            <div className="px-4 pb-4 pt-3 bg-background/40">
              <p className="text-xs text-foreground/80 leading-relaxed mb-3">{layer.desc}</p>
              <div className="flex flex-wrap gap-1.5">
                {layer.tech.map(t => (
                  <span key={t} className="text-xs bg-primary/10 text-primary/80 border border-primary/20 px-2 py-0.5 rounded font-mono">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
      {/* 데이터 흐름 요약 */}
      <div className="mt-4 rounded-xl border border-border bg-card/40 p-4">
        <p className="text-xs text-muted-foreground font-medium mb-2 uppercase tracking-wide">데이터 흐름</p>
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          {['사용자 입력 (음성/텍스트)', 'Interface Layer', 'API & Logic Layer', 'RPA / AI Agents', '결과 보고'].map((step, i, arr) => (
            <span key={i} className="flex items-center gap-2">
              <span className="bg-muted/60 border border-border/60 px-2 py-1 rounded text-foreground/80">{step}</span>
              {i < arr.length - 1 && <ArrowRight className="w-3 h-3 text-muted-foreground flex-shrink-0" />}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── 5대 도메인 섹션 ─────────────────────────────────────────
function DomainsSection() {
  return (
    <section id="domains" className="mb-12">
      <h2 className="text-xl font-bold text-foreground mb-1 flex items-center gap-2">
        <Layers className="w-5 h-5 text-primary" />
        5+1 핵심 도메인
      </h2>
      <p className="text-sm text-muted-foreground mb-6">
        모든 기능을 6개 도메인으로 구조화 — 실질적 적용 시나리오 및 기술 용어 포함
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {DOMAINS.map(domain => (
          <motion.div key={domain.id} variants={staggerItem}
            className={`rounded-2xl border p-5 ${domain.color}`}
            style={{ boxShadow: '0 2px 12px -4px rgba(0,0,0,0.3)' }}>
            <div className="flex items-center gap-3 mb-3">
              <span className="text-2xl">{domain.icon}</span>
              <div>
                <h3 className="font-bold text-foreground text-sm">{domain.title}</h3>
                <p className="text-xs text-muted-foreground font-mono">{domain.titleEn}</p>
              </div>
            </div>
            <p className="text-xs text-foreground/80 leading-relaxed mb-3 border-l-2 border-primary/40 pl-3">
              <span className="text-muted-foreground font-medium">시나리오: </span>
              {domain.useCase}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {domain.techTerms.map(t => (
                <span key={t} className="text-xs bg-background/50 border border-border/60 text-muted-foreground px-2 py-0.5 rounded font-mono">
                  {t}
                </span>
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

// ─── 로드맵 섹션 ─────────────────────────────────────────────
function RoadmapSection() {
  return (
    <section id="roadmap" className="mb-12">
      <h2 className="text-xl font-bold text-foreground mb-1 flex items-center gap-2">
        <Clock className="w-5 h-5 text-primary" />
        단계별 실행 계획
      </h2>
      <p className="text-sm text-muted-foreground mb-6">
        초기 과부하 방지를 위한 3-Phase 분할 — MVP 검증 후 점진적 고도화
      </p>
      <div className="space-y-4">
        {TIMELINE_PHASES.map((phase) => (
          <motion.div key={phase.phase} variants={staggerItem}
            className="rounded-2xl border border-border overflow-hidden"
            style={{ boxShadow: '0 4px 20px -6px rgba(0,0,0,0.35)' }}>
            <div className={`p-4 border-b border-border/60 flex items-center justify-between gap-4 ${
              phase.phase === 1 ? 'bg-blue-500/10' : phase.phase === 2 ? 'bg-violet-500/10' : 'bg-emerald-500/10'
            }`}>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded-full ${PHASE_COLOR[phase.phase]}`}>
                    Phase {phase.phase}
                  </span>
                  <span className="text-xs text-muted-foreground font-mono">{phase.duration}</span>
                </div>
                <h3 className="font-bold text-foreground">{phase.title}</h3>
                <p className="text-xs text-muted-foreground mt-0.5">{phase.description}</p>
              </div>
            </div>
            <div className="p-4 bg-background/40">
              <ul className="space-y-2">
                {phase.todos.map((todo, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-xs text-foreground/80">
                    <span className="w-4 h-4 rounded border border-border/80 bg-muted/40 flex-shrink-0 mt-0.5 flex items-center justify-center">
                      <span className="w-1.5 h-1.5 rounded-sm bg-muted-foreground/40" />
                    </span>
                    <span className="leading-relaxed">{todo}</span>
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

// ─── 통계 카드 ──────────────────────────────────────────────
interface StatCardProps { icon: React.ReactNode; value: string | number; label: string; sub?: string }
function StatCard({ icon, value, label, sub }: StatCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card/80 p-4 flex items-center gap-3"
      style={{ boxShadow: '0 2px 12px -4px rgba(0,0,0,0.3)' }}>
      <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary flex-shrink-0">
        {icon}
      </div>
      <div>
        <div className="text-2xl font-bold font-mono text-foreground leading-none">{value}</div>
        <div className="text-xs text-muted-foreground mt-0.5">{label}</div>
        {sub && <div className="text-xs text-accent mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

// ─── 네비게이션 ──────────────────────────────────────────────
function NavBar() {
  const links = [
    { id: 'overview', label: '개요' },
    { id: 'architecture', label: '아키텍처' },
    { id: 'domains', label: '도메인' },
    { id: 'roadmap', label: '로드맵' },
    { id: 'features', label: '기능 목록' },
  ];
  return (
    <nav className="sticky top-0 z-50 bg-background/90 border-b border-border"
      style={{ backdropFilter: 'blur(12px)' }}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
            <Zap className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-bold text-foreground text-sm font-mono">{SERVICE_NAME}</span>
          <span className="text-xs text-muted-foreground hidden sm:block">{SERVICE_VERSION}</span>
        </div>
        <div className="flex items-center gap-0.5 overflow-x-auto">
          {links.map(item => (
            <button key={item.id}
              onClick={() => document.getElementById(item.id)?.scrollIntoView({ behavior: 'smooth' })}
              className="px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-lg transition-colors whitespace-nowrap">
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </nav>
  );
}

// ─── 메인 페이지 ─────────────────────────────────────────────
export default function Home() {
  const totalFeatures    = CATEGORIES.reduce((s, c) => s + c.features.length, 0);
  const totalSubFeatures = CATEGORIES.reduce((s, c) => s + c.features.reduce((ss, f) => ss + f.subFeatures.length, 0), 0);
  const p0Count          = CATEGORIES.reduce((s, c) => s + c.features.filter(f => f.priority === 'P0').length, 0);
  const totalTechTags    = new Set(CATEGORIES.flatMap(c => c.features.flatMap(f => f.techTags))).size;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <NavBar />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10">

        {/* ── 히어로 ─────────────────────────── */}
        <section id="overview" className="mb-12">
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={springPresets.gentle}>

            <div className="mb-4 flex flex-wrap items-center gap-2">
              <span className="text-xs font-mono text-muted-foreground bg-muted/60 border border-border px-3 py-1 rounded-full">
                {SERVICE_VERSION}
              </span>
              <span className="text-xs font-mono text-primary bg-primary/10 border border-primary/20 px-3 py-1 rounded-full">
                Core Value: {CORE_VALUE}
              </span>
              <span className="text-xs font-mono text-muted-foreground bg-muted/60 border border-border px-3 py-1 rounded-full">
                {ARCH_STACK}
              </span>
            </div>

            <h1 className="text-4xl sm:text-5xl font-bold text-foreground leading-tight mb-2">
              {SERVICE_NAME}
            </h1>
            <p className="text-xl text-primary font-semibold mb-2">{SERVICE_FULL}</p>
            <p className="text-base text-muted-foreground max-w-2xl leading-relaxed mb-8">
              {SERVICE_TAGLINE}
            </p>

            {/* 통계 */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
              <StatCard icon={<Layers className="w-4 h-4" />}     value={CATEGORIES.length} label="카테고리" sub="전 영역 커버" />
              <StatCard icon={<CheckSquare className="w-4 h-4" />} value={totalFeatures}     label="기능"     sub="총 기능 수" />
              <StatCard icon={<Zap className="w-4 h-4" />}         value={p0Count}           label="핵심 기능" sub="즉시 구현" />
              <StatCard icon={<Code2 className="w-4 h-4" />}       value={totalTechTags}     label="기술 스택" sub="고유 기술 수" />
            </div>

            {/* 서비스 비전 */}
            <div className="rounded-2xl border border-border bg-card/60 p-6 mb-6"
              style={{ boxShadow: '0 4px 24px -8px rgba(0,0,0,0.4)' }}>
              <h2 className="font-bold text-foreground text-lg mb-3 flex items-center gap-2">
                <Target className="w-5 h-5 text-primary" />
                서비스 비전 & 핵심 목표
              </h2>
              <p className="text-sm text-foreground/80 leading-relaxed mb-5">
                <strong className="text-foreground">{SERVICE_NAME}</strong>은 인지(LLM/Vision)와 실행(RPA/API)을 결합하여,
                사용자의 개입을 최소화하고 <strong className="text-primary">ROI(시간 투자 대비 효용)를 극대화하는 자율형 AI 비서</strong>입니다.
                목표 아키텍처는 React(프론트엔드)와 FastAPI(고성능 비동기 백엔드)를 기반으로 구축하며,
                Docker 컨테이너화를 통해 각 자동화 모듈을 독립적으로 배포·관리합니다.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  { icon: '🎙️', title: 'Zero-Click 환경',   desc: '음성·프롬프트만으로 모든 명령 실행. 타이핑·마우스 클릭 최소화' },
                  { icon: '🤖', title: '자율 실행 & 보고',  desc: 'AI가 계획·실행·수정까지 자율 처리. 사용자는 결과 승인만' },
                  { icon: '🔧', title: 'LLM + RPA 결합',  desc: '언어 이해(LLM)와 실제 행동(RPA)을 통합한 엔드투엔드 자동화' },
                ].map(item => (
                  <div key={item.title} className="rounded-xl bg-muted/30 border border-border/60 p-4">
                    <div className="text-2xl mb-2">{item.icon}</div>
                    <h4 className="font-semibold text-foreground text-sm mb-1">{item.title}</h4>
                    <p className="text-xs text-muted-foreground leading-relaxed">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* 범례 */}
            <div className="flex flex-wrap items-center gap-4 p-4 rounded-xl border border-border bg-card/40 text-xs">
              <span className="text-muted-foreground font-medium">우선순위:</span>
              {Object.entries(PRIORITY_LABEL).map(([key, label]) => (
                <div key={key} className="flex items-center gap-1.5">
                  <span className={`px-2 py-0.5 rounded-full font-mono font-medium ${PRIORITY_STYLE[key]}`}>{label}</span>
                  <span className="text-muted-foreground">{key === 'P0' ? '즉시' : key === 'P1' ? '핵심' : '추후'}</span>
                </div>
              ))}
              <span className="text-muted-foreground font-medium ml-2">
                <Sparkles className="w-3 h-3 inline mr-1 text-accent" />장점: 각 기능 카드에 표시
              </span>
            </div>
          </motion.div>
        </section>

        {/* ── 아키텍처 ────────────────────────── */}
        <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.1 }}>
          <ArchSection />
        </motion.div>

        {/* ── 5+1 도메인 ──────────────────────── */}
        <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.1 }}>
          <DomainsSection />
        </motion.div>

        {/* ── 로드맵 ──────────────────────────── */}
        <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.1 }}>
          <RoadmapSection />
        </motion.div>

        {/* ── 전체 기능 목록 ───────────────────── */}
        <section id="features">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-foreground mb-1 flex items-center gap-2">
              <Layers className="w-5 h-5 text-primary" />
              전체 기능 명세
            </h2>
            <p className="text-sm text-muted-foreground">
              {CATEGORIES.length}개 카테고리 · {totalFeatures}개 기능 · {totalSubFeatures}개 세부 항목
              <span className="ml-2 text-accent">
                <Sparkles className="w-3 h-3 inline mr-1" />장점 및 기술 태그 포함
              </span>
            </p>
          </div>
          <motion.div variants={staggerContainer} initial="hidden" whileInView="visible"
            viewport={{ once: true, amount: 0.05 }} className="space-y-6">
            {CATEGORIES.map((cat, index) => (
              <CategorySection key={cat.id} cat={cat} index={index} />
            ))}
          </motion.div>
        </section>

        {/* ── 푸터 ─────────────────────────────── */}
        <footer className="mt-16 pt-8 border-t border-border text-center">
          <p className="text-xs text-muted-foreground font-mono">{SERVICE_NAME} — {SERVICE_FULL}</p>
          <p className="text-xs text-muted-foreground/60 mt-1">{SERVICE_VERSION} · 통합 기획안</p>
        </footer>
      </main>
    </div>
  );
}
