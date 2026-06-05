import { useScrollReveal } from '../hooks/useScrollReveal';

const BADGES = ['AWS', 'Google', 'Anthropic', 'OpenAI', 'Microsoft'];

export default function TrustedBy() {
  const ref = useScrollReveal();

  return (
    <section
      className="w-full py-16 px-4 sm:px-6"
      style={{ backgroundColor: '#FFFFFF', borderTop: '1px solid #E5E7EB' }}
    >
      <div ref={ref} className="reveal max-w-4xl mx-auto text-center">
        <p
          style={{
            fontSize: '12px',
            color: '#9CA3AF',
            textTransform: 'uppercase',
            letterSpacing: '0.12em',
            fontWeight: '500',
            marginBottom: '28px',
          }}
        >
          Trusted by builders from
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6">
          {BADGES.map((name, i) => (
            <span
              key={name}
              style={{
                fontSize: '13px',
                fontWeight: '600',
                color: '#9CA3AF',
                padding: '8px 20px',
                border: '1px solid #E5E7EB',
                cursor: 'default',
                transition: 'color 0.2s ease',
                transitionDelay: `${i * 0.05}s`,
                userSelect: 'none',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = '#0A0A0A'; }}
              onMouseLeave={e => { e.currentTarget.style.color = '#9CA3AF'; }}
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
