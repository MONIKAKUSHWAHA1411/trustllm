export default function Footer() {
  return (
    <footer className="w-full bg-white border-t border-[#E5E7EB] py-10 px-4 sm:px-6">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <span
            style={{ backgroundColor: '#E8420A' }}
            className="w-6 h-6 rounded flex items-center justify-center text-white text-xs font-bold"
          >
            T
          </span>
          <span className="font-bold text-[#0A0A0A] text-sm tracking-tight">TrustLLM</span>
        </div>

        {/* Nav links */}
        <div className="flex flex-wrap justify-center gap-5">
          {[
            ['How It Works', '#how-it-works'],
            ['Features',     '#features'],
            ['Leaderboard',  '/leaderboard'],
            ['RAG Testing',  '/rag-testing'],
            ['Sign In',      '/sign-in'],
          ].map(([label, href]) => (
            <a key={label} href={href} className="text-xs text-[#6B7280] hover:text-[#0A0A0A] transition-colors">
              {label}
            </a>
          ))}
        </div>

        {/* Copyright */}
        <p className="text-xs text-[#9CA3AF] text-center sm:text-right">
          © 2025 TrustLLM · Built by{' '}
          <a
            href="https://www.linkedin.com/in/monika-kushwaha-52443735/"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#E8420A' }}
            className="hover:opacity-70 transition-opacity"
          >
            Monika Kushwaha
          </a>
        </p>
      </div>
    </footer>
  );
}
