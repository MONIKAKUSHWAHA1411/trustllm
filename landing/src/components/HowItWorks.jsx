import { useScrollReveal } from '../hooks/useScrollReveal';

const STEPS = [
  { num: '01', title: 'Connect Your Models', desc: 'Add your LLM endpoint or paste an API key for OpenAI, Anthropic, Google, Groq, or any OpenAI-compatible API.' },
  { num: '02', title: 'Select Dimensions',   desc: 'Choose from Safety, Fairness, Robustness, Privacy, Truthfulness, and Machine Ethics — or run the full suite.' },
  { num: '03', title: 'Run Adversarial Prompts', desc: '500+ curated prompts probe jailbreaks, bias, hallucination traps, privacy leaks, and more.' },
  { num: '04', title: 'Get Scored Verdicts', desc: 'Each response is scored by a judge LLM and rule-based classifiers into per-dimension scores and a Trust Score.' },
  { num: '05', title: 'Compare & Decide',    desc: 'Side-by-side leaderboard shows where each model excels and fails. Export reports for evidence-based deployment.' },
];

export default function HowItWorks() {
  const sectionRef = useScrollReveal();

  return (
    /* Animated gradient background section */
    <section
      id="how-it-works"
      ref={sectionRef}
      className="reveal w-full py-24 px-4 sm:px-6"
      style={{ animation: 'gradientShift 6s ease-in-out infinite' }}
    >
      <div className="max-w-4xl mx-auto">
        <p className="text-xs font-semibold tracking-widest uppercase text-[#E8420A] mb-3">— HOW IT WORKS</p>
        <h2 className="text-3xl sm:text-4xl font-bold text-[#0A0A0A] tracking-tight mb-14">
          5 Steps to a Trust Score.
        </h2>

        <div className="flex flex-col divide-y divide-[#E5E7EB]">
          {STEPS.map(({ num, title, desc }, i) => (
            <div
              key={num}
              className="reveal flex gap-5 py-7 items-start"
              style={{ transitionDelay: `${i * 0.08}s` }}
            >
              <div
                style={{ backgroundColor: '#E8420A' }}
                className="flex-shrink-0 w-9 h-9 flex items-center justify-center text-white text-xs font-bold rounded-sm"
              >
                {num}
              </div>
              <div>
                <div className="font-semibold text-[#0A0A0A] mb-1">{title}</div>
                <div className="text-sm text-[#6B7280] leading-relaxed">{desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
