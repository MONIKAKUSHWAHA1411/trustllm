import { useState } from 'react';
import { useScrollReveal } from '../hooks/useScrollReveal';

export default function CTASection() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const ref = useScrollReveal();

  function handleSubmit(e) {
    e.preventDefault();
    // TODO: wire up to real email capture (e.g. ConvertKit, Mailchimp, or Supabase)
    console.log('Email submitted:', email);
    setSent(true);
    setEmail('');
  }

  return (
    <section
      className="w-full py-24 px-4 sm:px-6"
      style={{ backgroundColor: '#F9FAFB', borderTop: '1px solid #E5E7EB' }}
    >
      <div ref={ref} className="reveal max-w-2xl mx-auto text-center">
        <p
          style={{
            fontSize: '11px',
            fontWeight: '600',
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            color: '#E8420A',
            marginBottom: '16px',
          }}
        >
          — STAY UPDATED
        </p>
        <h2
          style={{
            fontSize: 'clamp(1.6rem, 3.5vw, 2.2rem)',
            fontWeight: '800',
            color: '#0A0A0A',
            letterSpacing: '-0.02em',
            marginBottom: '16px',
            lineHeight: '1.2',
          }}
        >
          Stay ahead of LLM evaluation.
        </h2>
        <p style={{ color: '#6B7280', fontSize: '15px', marginBottom: '36px', lineHeight: '1.6' }}>
          Updates on new models, eval techniques, and TrustLLM features.
        </p>

        {sent ? (
          <p style={{ color: '#E8420A', fontWeight: '600', fontSize: '14px' }}>
            ✓ You're on the list — we'll be in touch soon.
          </p>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto"
          >
            <input
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="your@email.com"
              className="flex-1 px-4 py-3 text-sm bg-white outline-none rounded-md transition-all"
              style={{
                border: '1px solid #E5E7EB',
                color: '#0A0A0A',
              }}
              onFocus={e => { e.currentTarget.style.borderColor = '#E8420A'; }}
              onBlur={e => { e.currentTarget.style.borderColor = '#E5E7EB'; }}
            />
            <button
              type="submit"
              style={{ backgroundColor: '#E8420A' }}
              className="px-6 py-3 text-white text-sm font-semibold rounded-md transition-all whitespace-nowrap"
              onMouseEnter={e => { e.currentTarget.style.backgroundColor = '#C23308'; }}
              onMouseLeave={e => { e.currentTarget.style.backgroundColor = '#E8420A'; }}
            >
              Subscribe →
            </button>
          </form>
        )}

        <p style={{ fontSize: '12px', color: '#9CA3AF', marginTop: '16px' }}>
          No spam. Unsubscribe anytime.
        </p>
      </div>
    </section>
  );
}
