import { useRef, useEffect } from 'react';

const CARDS = [
  {
    title: 'Single Prompt Eval',
    desc: 'Test any prompt against a model instantly. See trust scores across all six dimensions in real time.',
    href: '/run-evaluation',
  },
  {
    title: 'Batch Evaluation',
    desc: 'Run your full prompt dataset through multiple models at once. Compare results side-by-side at scale.',
    href: '/leaderboard',
  },
  {
    title: 'RAG Testing',
    desc: 'Upload documents, build a ChromaDB vector store, and evaluate retrieval faithfulness and grounding.',
    href: '/rag-testing',
  },
  {
    title: 'Agent Performance',
    desc: 'Benchmark autonomous agents on tool-call accuracy, hallucination rate, and semantic correctness.',
    href: '/run-evaluation',
  },
];

function FeatureCard({ title, desc, href, delay }) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { el.classList.add('visible'); observer.unobserve(el); } },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className="reveal bg-white border border-[#E5E7EB] p-6 flex flex-col gap-4 cursor-pointer transition-all duration-300 hover:-translate-y-1"
      style={{ transitionDelay: `${delay}s`, boxSizing: 'border-box' }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = '#E8420A';
        e.currentTarget.style.boxShadow = '0 8px 24px rgba(232,66,10,0.12)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = '#E5E7EB';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <div>
        <h3 className="font-semibold text-[#0A0A0A] text-base mb-1.5">{title}</h3>
        <p className="text-sm text-[#6B7280] leading-relaxed">{desc}</p>
      </div>
      <a
        href={href}
        style={{ color: '#E8420A' }}
        className="text-sm font-semibold mt-auto hover:opacity-70 transition-opacity"
      >
        Explore →
      </a>
    </div>
  );
}

export default function FeatureCards() {
  const titleRef = useRef(null);

  useEffect(() => {
    const el = titleRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { el.classList.add('visible'); observer.unobserve(el); } },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="features" className="w-full bg-white py-24 px-4 sm:px-6 border-t border-[#E5E7EB]">
      <div className="max-w-6xl mx-auto">
        <div ref={titleRef} className="reveal mb-12">
          <p className="text-xs font-semibold tracking-widest uppercase text-[#E8420A] mb-3">— FEATURES</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-[#0A0A0A] tracking-tight">
            Everything you need to trust your LLM.
          </h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {CARDS.map((card, i) => (
            <FeatureCard key={card.title} {...card} delay={i * 0.1} />
          ))}
        </div>
      </div>
    </section>
  );
}
