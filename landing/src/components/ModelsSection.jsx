import { useRef, useEffect } from 'react';

const MODEL_PROVIDERS = [
  { provider: 'OpenAI',     models: ['gpt-4o',               'gpt-4-turbo'] },
  { provider: 'Anthropic',  models: ['claude-3-opus',        'claude-3-sonnet'] },
  { provider: 'Google',     models: ['gemini-1.5-pro',       'gemini-1.5-flash'] },
  { provider: 'Groq',       models: ['llama3-70b-8192',      'mixtral-8x7b'] },
  { provider: 'Mistral',    models: ['mistral-large-latest', 'mistral-7b-instruct'] },
  { provider: 'Microsoft',  models: ['phi-3-medium-4k',      'phi-3-mini-4k'] },
];

function ProviderCard({ provider, models, delay }) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { el.classList.add('visible'); obs.unobserve(el); } },
      { threshold: 0.1 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className="reveal"
      style={{
        backgroundColor: '#F9FAFB',
        border: '1px solid #E5E7EB',
        padding: '20px',
        transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
        transitionDelay: `${delay}s`,
        cursor: 'default',
        textAlign: 'left',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = '#E8420A';
        e.currentTarget.style.boxShadow = '0 4px 16px rgba(232,66,10,0.08)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = '#E5E7EB';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <div style={{ fontWeight: '700', color: '#0A0A0A', fontSize: '14px', marginBottom: '8px' }}>
        {provider}
      </div>
      {models.map(m => (
        <div
          key={m}
          style={{
            fontSize: '12px',
            color: '#6B7280',
            fontFamily: 'var(--mono)',
            lineHeight: '1.8',
          }}
        >
          {m}
        </div>
      ))}
    </div>
  );
}

export default function ModelsSection() {
  const titleRef = useRef(null);

  useEffect(() => {
    const el = titleRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { el.classList.add('visible'); obs.unobserve(el); } },
      { threshold: 0.1 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <section
      id="models"
      className="w-full py-24 px-4 sm:px-6"
      style={{ backgroundColor: '#F9FAFB', borderTop: '1px solid #E5E7EB' }}
    >
      <div className="max-w-6xl mx-auto">

        {/* Header */}
        <div ref={titleRef} className="reveal mb-12" style={{ textAlign: 'left' }}>
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
            — MODELS
          </p>
          <h2
            style={{
              fontSize: 'clamp(1.8rem, 4vw, 2.4rem)',
              fontWeight: '800',
              letterSpacing: '-0.02em',
              lineHeight: '1.15',
              marginBottom: '12px',
            }}
          >
            <span style={{ color: '#0A0A0A' }}>12 Models.</span>{' '}
            <span style={{ color: '#E8420A' }}>One Platform.</span>
          </h2>

          {/* providers.py chip */}
          <code
            style={{
              display: 'inline-block',
              padding: '4px 10px',
              backgroundColor: '#FFF1EE',
              border: '1px solid #E8420A',
              color: '#C23308',
              fontFamily: 'var(--mono)',
              fontSize: '13px',
              borderRadius: '4px',
              marginBottom: '10px',
            }}
          >
            providers.py
          </code>

          <p style={{ fontSize: '14px', color: '#6B7280', marginTop: '6px' }}>
            No vendored adapters, no surprises.
          </p>
        </div>

        {/* Provider grid — 1-col on mobile, 3-col on sm+ */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {MODEL_PROVIDERS.map((p, i) => (
            <ProviderCard
              key={p.provider}
              provider={p.provider}
              models={p.models}
              delay={i * 0.06}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
