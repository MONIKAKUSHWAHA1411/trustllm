import { useState, useEffect } from 'react';
import { X } from 'lucide-react';

const STORAGE_KEY = 'aaif-banner-dismissed';

export default function AnnouncementBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) setVisible(true);
  }, []);

  function dismiss() {
    localStorage.setItem(STORAGE_KEY, '1');
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div
      style={{ backgroundColor: '#E8420A', fontSize: '13px' }}
      className="w-full text-white py-2 px-4 flex items-center justify-center relative"
    >
      <span className="font-medium flex items-center gap-2">
        ✦ TrustLLM now supports RAG evaluation —{' '}
        <a
          href="/rag-testing"
          className="underline underline-offset-2 font-semibold hover:opacity-80 transition-opacity"
        >
          Try it →
        </a>
      </span>
      <button
        onClick={dismiss}
        aria-label="Dismiss announcement"
        className="absolute right-4 top-1/2 -translate-y-1/2 hover:opacity-70 transition-opacity text-white"
      >
        <X size={16} />
      </button>
    </div>
  );
}
