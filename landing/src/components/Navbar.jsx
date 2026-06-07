import { useState } from 'react';
import { Menu, X } from 'lucide-react';

const NAV_LINKS = [
  { label: 'Features',    href: '#features' },
  { label: 'How It Works',href: '#how-it-works' },
  { label: 'Leaderboard', href: '/leaderboard' },
  { label: 'RAG Testing', href: '/rag-testing' },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-40 w-full bg-white border-b border-[#E5E7EB]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <a href="/" className="flex items-center gap-2 no-underline">
          <span
            style={{ backgroundColor: '#E8420A' }}
            className="w-7 h-7 rounded-[5px] flex items-center justify-center text-white text-sm font-bold select-none"
          >
            T
          </span>
          <span className="font-bold text-[#0A0A0A] text-base tracking-tight">TrustLLM</span>
        </a>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-8" style={{ marginLeft: '32px' }}>
          {NAV_LINKS.map(({ label, href }) => (
            <a
              key={label}
              href={href}
              className="text-sm font-medium text-[#6B7280] hover:text-[#0A0A0A] transition-colors relative group"
            >
              {label}
              <span
                style={{ backgroundColor: '#E8420A' }}
                className="absolute -bottom-0.5 left-0 h-0.5 w-0 group-hover:w-full transition-all duration-200"
              />
            </a>
          ))}
        </div>

        {/* CTA */}
        <div className="hidden md:flex items-center gap-3">
          <a
            href="/sign-in"
            className="text-sm font-medium text-[#0A0A0A] hover:text-[#E8420A] transition-colors"
          >
            Sign in
          </a>
          <a
            href="/sign-in"
            style={{ backgroundColor: '#E8420A' }}
            className="text-sm font-semibold text-white px-4 py-2 rounded-md hover:opacity-90 transition-opacity"
            onMouseEnter={e => e.currentTarget.style.backgroundColor = '#C23308'}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = '#E8420A'}
          >
            Join Now →
          </a>
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden text-[#0A0A0A]"
          onClick={() => setOpen(!open)}
          aria-label="Toggle menu"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-white border-t border-[#E5E7EB] px-4 py-4 flex flex-col gap-4">
          {NAV_LINKS.map(({ label, href }) => (
            <a key={label} href={href} className="text-sm font-medium text-[#0A0A0A]" onClick={() => setOpen(false)}>
              {label}
            </a>
          ))}
          <a
            href="/sign-in"
            style={{ backgroundColor: '#E8420A' }}
            className="text-sm font-semibold text-white px-4 py-2 rounded-md text-center"
            onClick={() => setOpen(false)}
          >
            Join Now →
          </a>
        </div>
      )}
    </nav>
  );
}
