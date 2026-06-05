const NAV_LINKS = [
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Trust dimensions', href: '#how-it-works' },
  { label: 'Models', href: '#models' },
  { label: 'Sign in', href: '/sign-in' },
];

export default function Footer() {
  return (
    <footer
      style={{
        backgroundColor: '#F9FAFB',
        borderTop: '1px solid #E5E7EB',
        padding: '32px 16px',
        textAlign: 'center',
        boxSizing: 'border-box',
        width: '100%',
      }}
    >
      {/* Nav links row */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: '16px',
          marginBottom: '12px',
        }}
      >
        {NAV_LINKS.map(({ label, href }) => (
          <a
            key={label}
            href={href}
            style={{ fontSize: '14px', color: '#6B7280', textDecoration: 'none', transition: 'color 0.15s' }}
            onMouseEnter={e => { e.currentTarget.style.color = '#E8420A'; }}
            onMouseLeave={e => { e.currentTarget.style.color = '#6B7280'; }}
          >
            {label}
          </a>
        ))}
      </div>

      {/* Copyright row */}
      <p
        style={{
          fontSize: '13px',
          color: '#6B7280',
          lineHeight: '1.6',
          margin: 0,
        }}
      >
        © 2025 TrustLLM · AI Model Evaluation Platform · Powered by ChromaDB · Groq · Streamlit · Built by{' '}
        <a
          href="https://www.linkedin.com/in/monika-kushwaha-52443735"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: '#E8420A', textDecoration: 'none' }}
          onMouseEnter={e => { e.currentTarget.style.textDecoration = 'underline'; }}
          onMouseLeave={e => { e.currentTarget.style.textDecoration = 'none'; }}
        >
          Monika Kushwaha
        </a>
      </p>
    </footer>
  );
}
