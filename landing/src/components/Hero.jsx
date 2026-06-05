import { useState, useEffect } from 'react';

const ROTATING_WORDS = ['Truthfulness', 'Safety', 'Fairness', 'Robustness', 'Privacy', 'Ethics'];
const INTERVAL_MS = 2000;

export default function Hero() {
  const [index, setIndex] = useState(0);
  const [animKey, setAnimKey] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex(i => (i + 1) % ROTATING_WORDS.length);
      setAnimKey(k => k + 1);
    }, INTERVAL_MS);
    return () => clearInterval(timer);
  }, []);

  return (
    <section className="w-full bg-white pt-20 pb-24 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#E5E7EB] text-xs font-medium text-[#6B7280] mb-8">
          <span style={{ backgroundColor: '#E8420A' }} className="w-1.5 h-1.5 rounded-full inline-block" />
          AI Model Trust Evaluation Platform
        </div>

        {/* Headline with rotating word */}
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-[#0A0A0A] leading-tight tracking-tight mb-6">
          Evaluate{' '}
          <span
            key={animKey}
            style={{
              color: '#E8420A',
              display: 'inline-block',
              animation: `wordFadeSlide ${INTERVAL_MS}ms ease-in-out forwards`,
            }}
          >
            {ROTATING_WORDS[index]}
          </span>
          <br className="hidden sm:block" />
          {' '}in every LLM response.
        </h1>

        {/* Subheading */}
        <p className="text-base sm:text-lg text-[#6B7280] max-w-2xl mx-auto mb-10 leading-relaxed">
          Run rigorous trust benchmarks across six dimensions. Get verdicts, not vanity metrics.
          Built for teams who deploy LLMs in production.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <a
            href="/sign-in"
            style={{ backgroundColor: '#E8420A' }}
            className="inline-flex items-center gap-2 px-6 py-3 text-white font-semibold text-sm rounded-md transition-all"
            onMouseEnter={e => e.currentTarget.style.backgroundColor = '#C23308'}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = '#E8420A'}
          >
            Start Evaluating →
          </a>
          <a
            href="#how-it-works"
            className="inline-flex items-center gap-2 px-6 py-3 text-[#0A0A0A] font-medium text-sm border border-[#E5E7EB] rounded-md hover:border-[#E8420A] hover:text-[#E8420A] transition-all"
          >
            See how it works
          </a>
        </div>

        {/* Trust badges */}
        <div className="mt-14 flex flex-wrap items-center justify-center gap-6 text-xs text-[#9CA3AF]">
          {['No GPU required', 'Local inference', 'RAG-ready', 'Open evaluation prompts'].map(badge => (
            <span key={badge} className="flex items-center gap-1.5">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <circle cx="6" cy="6" r="6" fill="#E8420A" opacity="0.15"/>
                <path d="M3.5 6l1.8 1.8L8.5 4" stroke="#E8420A" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              {badge}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
