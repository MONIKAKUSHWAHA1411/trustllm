import { useScrollReveal } from '../hooks/useScrollReveal';

const BADGES = ['AWS', 'Google', 'Anthropic', 'OpenAI', 'Microsoft'];

export default function TrustedBy() {
  const ref = useScrollReveal();

  return (
    <section className="w-full bg-white py-16 px-4 sm:px-6 border-t border-[#E5E7EB]">
      <div ref={ref} className="reveal max-w-4xl mx-auto text-center">
        <p className="text-xs text-[#9CA3AF] uppercase tracking-widest font-medium mb-8">
          Trusted by teams building with
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-8">
          {BADGES.map((name, i) => (
            <span
              key={name}
              className="text-sm font-semibold text-[#9CA3AF] hover:text-[#0A0A0A] transition-colors cursor-default px-4 py-2 border border-[#E5E7EB] select-none"
              style={{ transitionDelay: `${i * 0.05}s` }}
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
