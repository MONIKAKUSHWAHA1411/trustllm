export default function Footer() {
  return (
    <footer
      style={{
        backgroundColor: '#F9FAFB',
        borderTop: '1px solid #E5E7EB',
        padding: '24px 16px',
        boxSizing: 'border-box',
        width: '100%',
      }}
    >
      <div
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          fontSize: '14px',
          color: '#6B7280',
        }}
      >
        {/* Left */}
        <span>© 2025 TrustLLM. All rights reserved.</span>

        {/* Right */}
        <span>
          Built with{' '}
          <a
            href="https://claude.ai"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#E8420A', textDecoration: 'none' }}
            onMouseEnter={e => { e.currentTarget.style.textDecoration = 'underline'; }}
            onMouseLeave={e => { e.currentTarget.style.textDecoration = 'none'; }}
          >
            Claude
          </a>
        </span>
      </div>
    </footer>
  );
}
