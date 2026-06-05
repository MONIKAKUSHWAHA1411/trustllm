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
    <section className="w-full py-24 px-4 sm:px-6 border-t border-[#E5E7EB]" style={{ backgroundColor: '#F9FAFB' }}>
      <div ref={ref} className="reveal max-w-2xl mx-auto text-center">
        <p className="text-xs font-semibold tracking-widest uppercase text-[#E8420A] mb-4">— GET STARTED</p>
        <h2 className="text-3xl sm:text-4xl font-bold text-[#0A0A0A] tracking-tight mb-4">
          Know before you ship.
        </h2>
        <p className="text-[#6B7280] text-base mb-10 leading-relaxed">
          Join teams using TrustLLM to benchmark LLMs before production. Get early access and evaluation tips.
        </p>

        {sent ? (
          <p className="text-[#E8420A] font-semibold text-sm">
            ✓ You're on the list — we'll be in touch soon.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
            <input
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="your@email.com"
              className="flex-1 px-4 py-3 text-sm border border-[#E5E7EB] bg-white text-[#0A0A0A] placeholder-[#9CA3AF] outline-none rounded-md transition-all"
              onFocus={e => e.currentTarget.style.borderColor = '#E8420A'}
              onBlur={e => e.currentTarget.style.borderColor = '#E5E7EB'}
            />
            <button
              type="submit"
              style={{ backgroundColor: '#E8420A' }}
              className="px-6 py-3 text-white text-sm font-semibold rounded-md transition-all whitespace-nowrap"
              onMouseEnter={e => e.currentTarget.style.backgroundColor = '#C23308'}
              onMouseLeave={e => e.currentTarget.style.backgroundColor = '#E8420A'}
            >
              Get Early Access →
            </button>
          </form>
        )}

        <p className="text-xs text-[#9CA3AF] mt-4">No spam. Unsubscribe anytime.</p>
      </div>
    </section>
  );
}
