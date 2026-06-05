import { useRef, useEffect, useState } from 'react';

/* ── Data ─────────────────────────────────────────────────────────── */
const PROVIDERS = [
  { name: 'Groq',     models: ['llama3-70b-8192',     'mixtral-8x7b'] },
  { name: 'Claude',   models: ['claude-3-opus',        'claude-3-sonnet'] },
  { name: 'GPT',      models: ['gpt-4o',               'gpt-4-turbo'] },
  { name: 'Gemini',   models: ['gemini-1.5-pro',       'gemini-1.5-flash'] },
  { name: 'Mistral',  models: ['mistral-large-latest', 'mistral-7b-instruct'] },
  { name: 'Phi',      models: ['phi-3-medium-4k',      'phi-3-mini-4k'] },
];

const EVAL_MODES = ['Run Evaluation', 'RAG Testing', 'Batch Dataset'];

const DIMS = [
  { label: 'Truthfulness', value: 0.92 },
  { label: 'Safety',       value: 0.88 },
  { label: 'Fairness',     value: 0.74 },
  { label: 'Privacy',      value: 0.81 },
  { label: 'Robustness',   value: 0.69 },
  { label: 'Ethics',       value: 0.85 },
];

const RESULT_CHIPS = [
  'Per-Eval Breakdown',
  'Per-Dimension Drill-down',
  'Model Comparison',
  'Export JSON',
  'Export CSV',
  'Leaderboard View',
];

const STEPS = [
  {
    num: '01',
    label: 'PROMPT INPUT',
    title: 'Connect Your Models',
    desc: 'Add your LLM endpoint or paste an API key for OpenAI, Anthropic, Google, Groq, or any OpenAI-compatible API.',
    content: null,
  },
  {
    num: '02',
    label: 'MODEL SELECTION',
    title: 'Pick from 12 models',
    desc: 'Six providers, two models each. Swap at any time — no re-configuration required.',
    content: 'providers',
  },
  {
    num: '03',
    label: 'EVAL PATH',
    title: 'Choose your test path',
    desc: 'Run a single prompt, test with a full dataset, or probe your RAG pipeline.',
    content: 'modes',
  },
  {
    num: '04',
    label: 'SCORING',
    title: 'Six dimensions, one trust score',
    desc: 'Every response is graded on Truthfulness, Safety, Fairness, Privacy, Robustness, and Ethics.',
    content: 'scores',
  },
  {
    num: '05',
    label: 'RESULTS',
    title: 'Slice it however you ship',
    desc: 'Per-model breakdown, per-dimension drill-down, and exportable reports — ready for your deployment review.',
    content: 'results',
  },
];

/* ── Step content sub-components ─────────────────────────────────── */
function ProvidersContent() {
  return (
    <div style={{ marginTop: '16px', textAlign: 'left' }}>
      {/* Provider pill row */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '14px' }}>
        {PROVIDERS.map(p => (
          <span
            key={p.name}
            style={{
              padding: '3px 10px',
              border: '1px solid #E8420A',
              color: '#E8420A',
              backgroundColor: '#FFF1EE',
              fontSize: '11px',
              fontWeight: '600',
              borderRadius: '4px',
              letterSpacing: '0.02em',
            }}
          >
            {p.name}
          </span>
        ))}
      </div>
      {/* 3-column model grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
        {PROVIDERS.map(p => (
          <div
            key={p.name}
            style={{
              padding: '10px 12px',
              backgroundColor: '#F9FAFB',
              border: '1px solid #E5E7EB',
              borderRadius: '4px',
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: '700', color: '#0A0A0A', marginBottom: '4px' }}>
              {p.name}
            </div>
            {p.models.map(m => (
              <div key={m} style={{ fontSize: '11px', color: '#6B7280', fontFamily: 'var(--mono)', lineHeight: '1.7' }}>
                {m}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function ModesContent() {
  const [active, setActive] = useState('Run Evaluation');
  return (
    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '16px', textAlign: 'left' }}>
      {EVAL_MODES.map(mode => (
        <button
          key={mode}
          onClick={() => setActive(mode)}
          style={{
            padding: '7px 14px',
            fontSize: '12px',
            fontWeight: '600',
            borderRadius: '4px',
            cursor: 'pointer',
            border: '1px solid #E8420A',
            backgroundColor: active === mode ? '#E8420A' : 'transparent',
            color: active === mode ? '#FFFFFF' : '#E8420A',
            transition: 'all 0.15s ease',
          }}
        >
          {mode}
        </button>
      ))}
    </div>
  );
}

function ScoresContent() {
  return (
    <div style={{ marginTop: '16px', textAlign: 'left' }}>
      {/* "example" label */}
      <div style={{ fontSize: '10px', color: '#9CA3AF', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '10px' }}>
        Example scores — not live data
      </div>
      {/* Progress bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
        {DIMS.map(({ label, value }) => (
          <div key={label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ fontSize: '12px', color: '#0A0A0A', fontWeight: '500' }}>{label}</span>
              <span style={{ fontSize: '12px', color: '#0A0A0A', fontWeight: '600' }}>{value.toFixed(2)}</span>
            </div>
            <div style={{ height: '6px', backgroundColor: '#F9FAFB', borderRadius: '3px', overflow: 'hidden', border: '1px solid #E5E7EB' }}>
              <div
                style={{
                  height: '100%',
                  width: `${value * 100}%`,
                  backgroundColor: '#E8420A',
                  borderRadius: '3px',
                }}
              />
            </div>
          </div>
        ))}
      </div>
      {/* Formula box */}
      <div
        style={{
          padding: '10px 14px',
          backgroundColor: '#FFF1EE',
          border: '1px solid #E8420A',
          borderRadius: '4px',
          fontFamily: 'var(--mono)',
          fontSize: '13px',
          color: '#C23308',
          letterSpacing: '0.02em',
        }}
      >
        Trust Score = Σ(6 dims) / 6
      </div>
    </div>
  );
}

function ResultsContent() {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '16px', textAlign: 'left' }}>
      {RESULT_CHIPS.map(chip => (
        <span
          key={chip}
          style={{
            padding: '5px 12px',
            border: '1px solid #E5E7EB',
            color: '#6B7280',
            backgroundColor: '#F9FAFB',
            fontSize: '12px',
            borderRadius: '4px',
          }}
        >
          {chip}
        </span>
      ))}
    </div>
  );
}

/* ── Single step row ─────────────────────────────────────────────── */
function StepRow({ step, isLast, delay }) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) { el.classList.add('visible'); obs.unobserve(el); }
      },
      { threshold: 0.08 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className="reveal"
      style={{ display: 'flex', gap: '0', alignItems: 'stretch', transitionDelay: `${delay}s` }}
    >
      {/* Timeline spine */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          width: '52px',
          flexShrink: 0,
        }}
      >
        {/* Number circle */}
        <div
          style={{
            width: '38px',
            height: '38px',
            borderRadius: '50%',
            border: '2px solid #E8420A',
            color: '#E8420A',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '11px',
            fontWeight: '700',
            backgroundColor: '#FFFFFF',
            flexShrink: 0,
            zIndex: 1,
            letterSpacing: '0.02em',
          }}
        >
          {step.num}
        </div>
        {/* Dashed connector to next step */}
        {!isLast && (
          <div
            style={{
              flex: 1,
              width: '2px',
              marginTop: '8px',
              marginBottom: '8px',
              background:
                'repeating-linear-gradient(to bottom, rgba(232,66,10,0.3) 0px, rgba(232,66,10,0.3) 5px, transparent 5px, transparent 11px)',
            }}
          />
        )}
      </div>

      {/* Card */}
      <div style={{ flex: 1, paddingBottom: isLast ? 0 : '28px' }}>
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E5E7EB',
            borderLeft: '3px solid #E8420A',
            padding: '20px 24px',
            textAlign: 'left',
          }}
        >
          {/* Step label */}
          <div
            style={{
              fontSize: '11px',
              color: '#E8420A',
              letterSpacing: '0.1em',
              fontWeight: '600',
              textTransform: 'uppercase',
              marginBottom: '8px',
            }}
          >
            {step.num} · {step.label}
          </div>
          {/* Title */}
          <h3
            style={{
              fontSize: '17px',
              fontWeight: '700',
              color: '#0A0A0A',
              marginBottom: '8px',
            }}
          >
            {step.title}
          </h3>
          {/* Description */}
          <p style={{ fontSize: '14px', color: '#6B7280', lineHeight: '1.65' }}>
            {step.desc}
          </p>
          {/* Rich content */}
          {step.content === 'providers' && <ProvidersContent />}
          {step.content === 'modes'     && <ModesContent />}
          {step.content === 'scores'    && <ScoresContent />}
          {step.content === 'results'   && <ResultsContent />}
        </div>
      </div>
    </div>
  );
}

/* ── Section ─────────────────────────────────────────────────────── */
export default function HowItWorks() {
  const titleRef = useRef(null);

  useEffect(() => {
    const el = titleRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) { el.classList.add('visible'); obs.unobserve(el); }
      },
      { threshold: 0.1 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <section
      id="how-it-works"
      className="w-full py-24 px-4 sm:px-6"
      style={{ animation: 'gradientShift 6s ease-in-out infinite' }}
    >
      <div className="max-w-4xl mx-auto">

        {/* Section header */}
        <div ref={titleRef} className="reveal mb-14" style={{ textAlign: 'left' }}>
          <p
            style={{
              fontSize: '11px',
              fontWeight: '600',
              letterSpacing: '0.15em',
              textTransform: 'uppercase',
              color: '#E8420A',
              marginBottom: '12px',
            }}
          >
            — HOW IT WORKS
          </p>
          <h2
            style={{
              fontSize: 'clamp(1.8rem, 4vw, 2.4rem)',
              fontWeight: '800',
              color: '#0A0A0A',
              letterSpacing: '-0.02em',
              lineHeight: '1.15',
            }}
          >
            5 Steps to a Trust Score.
          </h2>
        </div>

        {/* Timeline steps */}
        <div>
          {STEPS.map((step, i) => (
            <StepRow
              key={step.num}
              step={step}
              isLast={i === STEPS.length - 1}
              delay={i * 0.08}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
