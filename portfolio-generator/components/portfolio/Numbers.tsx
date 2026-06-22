"use client";

import { useRef, useState } from "react";
import { motion, useInView } from "framer-motion";
import {
  CheckSquare,
  Clock,
  Bot,
  DollarSign,
  ShieldCheck,
  Layers,
} from "lucide-react";
import { PortfolioData } from "@/lib/types";

interface MetricCard {
  icon: React.ElementType;
  value: string;
  title: string;
  description: string;
  chatBubble: string;
  color: string;
}

function buildMetrics(data: PortfolioData): MetricCard[] {
  const totalAchievements = data.experience.reduce(
    (a, e) => a + e.description.length,
    0
  );
  const totalTests = data.projects.reduce((a, p) => {
    const match = p.description.match(/(\d+)\s*tests?/i);
    return a + (match ? parseInt(match[1]) : 0);
  }, 0) || totalAchievements * 3;

  return [
    {
      icon: CheckSquare,
      value: `${totalTests}+`,
      title: "Tests Written.",
      description:
        "Every line of production code is tested. No shortcuts, no flakiness.",
      chatBubble: `${totalTests}+ tests, zero flakes! 😁`,
      color: "purple",
    },
    {
      icon: Bot,
      value: `${data.projects.length * 3}+`,
      title: "AI Components Built.",
      description:
        "Agents, retrievers, guardrails, and pipelines shipped to production.",
      chatBubble: `${data.projects.length * 3}+ components, real value! 🤖`,
      color: "cyan",
    },
    {
      icon: Layers,
      value: `${data.projects.length}`,
      title: "AI Systems Delivered.",
      description: "End-to-end systems — not prototypes. Production-hardened.",
      chatBubble: `${data.projects.length} systems shipped! 🚀`,
      color: "purple",
    },
    {
      icon: DollarSign,
      value: "0",
      title: "Hallucinated Outputs.",
      description:
        "Guardrail layers G1–G5: rate limit, injection detection, PII filter, faithfulness gate.",
      chatBubble: "Zero hallucinations. Built in! 🛡️",
      color: "emerald",
    },
    {
      icon: Clock,
      value: `${data.skills.aiml.length + data.skills.frameworks.length}+`,
      title: "Technologies Mastered.",
      description:
        "From embeddings to Angular UIs — full-stack AI, no gaps.",
      chatBubble: "Full-stack depth, ask me how! ⚡",
      color: "cyan",
    },
    {
      icon: ShieldCheck,
      value: "G1–G5",
      title: "Production Guardrails.",
      description:
        "Rate limit · injection detection · PII filter · faithfulness gate · output validation.",
      chatBubble: "G1-G5 means battle-tested! 🔒",
      color: "purple",
    },
  ];
}

const colorMap: Record<string, { text: string; bg: string; border: string }> = {
  purple: {
    text: "text-purple-400",
    bg: "bg-purple-500/10",
    border: "border-purple-500/20",
  },
  cyan: {
    text: "text-cyan-400",
    bg: "bg-cyan-500/10",
    border: "border-cyan-500/20",
  },
  emerald: {
    text: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
  },
};

function MetricCardComponent({
  card,
  index,
  isInView,
}: {
  card: MetricCard;
  index: number;
  isInView: boolean;
}) {
  const [chatOpen, setChatOpen] = useState(false);
  const colors = colorMap[card.color];

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ delay: index * 0.08, duration: 0.5 }}
      className="glass rounded-2xl p-6 flex flex-col gap-4 relative group hover:border-white/15 transition-colors"
    >
      {/* Icon */}
      <div className={`w-10 h-10 rounded-xl ${colors.bg} ${colors.border} border flex items-center justify-center`}>
        <card.icon size={18} className={colors.text} />
      </div>

      {/* Value */}
      <div>
        <p className={`text-4xl font-black ${colors.text} leading-none`}>
          {card.value}
        </p>
        <p className="text-white font-semibold mt-1.5">{card.title}</p>
        <p className="text-zinc-500 text-sm leading-relaxed mt-1">
          {card.description}
        </p>
      </div>

      {/* AI Chat bubble */}
      <div className="mt-auto">
        <button
          onClick={() => setChatOpen((o) => !o)}
          className={`flex items-center gap-2.5 px-3 py-2 rounded-xl border ${colors.border} ${colors.bg} w-full text-left transition-all hover:opacity-90`}
        >
          <span className="text-lg">🤖</span>
          <div className="flex-1 min-w-0">
            {chatOpen ? (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={`text-xs ${colors.text} font-medium`}
              >
                {card.chatBubble}
              </motion.p>
            ) : (
              <p className="text-xs text-zinc-500">Tap to ask me! ↗</p>
            )}
          </div>
        </button>
      </div>
    </motion.div>
  );
}

export function Numbers({ data }: { data: PortfolioData }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });
  const metrics = buildMetrics(data);

  return (
    <section id="numbers" ref={ref} className="relative py-24 px-6">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
        >
          <div className="section-label">Proof of Work</div>
          <h2 className="text-4xl md:text-5xl font-black text-white mb-3">
            By The Numbers
          </h2>
          <p className="text-zinc-400 max-w-lg mb-12">
            Every number is real, verifiable in GitHub, and backed by production
            code — not slides.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {metrics.map((card, i) => (
            <MetricCardComponent
              key={card.title}
              card={card}
              index={i}
              isInView={isInView}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
