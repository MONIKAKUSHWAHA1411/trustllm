export default function Footer() {
  const footerLinks = [
    ['How It Works', '#how-it-works'],
    ['Features',     '#features'],
    ['Models',       '#models'],
    ['Leaderboard',  '/leaderboard'],
    ['RAG Testing',  '/rag-testing'],
    ['Sign In',      '/sign-in'],
  ];

  return (
    <footer
      className="w-full py-10 px-4 sm:px-6"
      style={{ backgroundColor: '#F9FAFB', borderTop: '1px solid #E5E7EB' }}
    >
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">

        {/* Logo */}
        <div className="flex items-center gap-2">
          <span
            style={{ backgroundColor: '#E8420A' }}
            className="w-6 h-6 flex items-center justify-center text-white text-xs font-bold rounded-sm"
          >
            T
          </span>
          <span style={{ fontWeight: '700', color: '#0A0A0A', fontSize: '14px', letterSpacing: '-0.01em' }}>
            TrustLLM
          </span>
        </div>

        {/* Nav links */}
        <div className="flex flex-wrap justify-center gap-5">
          {footerLinks.map(([label, href]) => (
            <a
              key={label}
              href={href}
              style={{ fontSize: '12px', color: '#6B7280', textDecoration: 'none', transition: 'color 0.15s' }}
              onMouseEnter={e => { e.currentTarget.style.color = '#E8420A'; }}
              onMouseLeave={e => { e.currentTarget.style.color = '#6B7280'; }}
            >
              {label}
            </a>
          ))}
        </div>

        {/* Copyright */}
        <p style={{ fontSize: '12px', color: '#9CA3AF', textAlign: 'right' }}>
          © 2025 TrustLLM · Built by{' '}
          <a
            href="https://www.linkedin.com/in/monika-kushwaha-52443735/"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#E8420A', textDecoration: 'none' }}
            onMouseEnter={e => { e.currentTarget.style.opacity = '0.7'; }}
            onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
          >
            Monika Kushwaha
          </a>
        </p>
      </div>
    </footer>
  );
}
