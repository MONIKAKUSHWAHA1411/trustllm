"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { MapPin, Mail, Phone } from "lucide-react";
import { PortfolioData } from "@/lib/types";

export function About({ data }: { data: PortfolioData }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section id="about" ref={ref} className="relative py-24 px-6">
      {/* section divider */}
      <div className="section-divider max-w-7xl mx-auto mb-16" />

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={isInView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.55 }}
        >
          <div className="section-label">My Story</div>
          <h2 className="text-4xl md:text-5xl font-black text-white mb-6">
            Building AI That{" "}
            <span className="gradient-text">Survives Production</span>
          </h2>
          <p className="text-zinc-400 leading-relaxed text-base mb-6">
            {data.summary}
          </p>

          {/* Contact details */}
          <div className="flex flex-col gap-3">
            {data.location && (
              <div className="flex items-center gap-2 text-sm text-zinc-400">
                <MapPin size={14} className="text-purple-400 shrink-0" />
                {data.location}
              </div>
            )}
            {data.email && (
              <div className="flex items-center gap-2 text-sm text-zinc-400">
                <Mail size={14} className="text-cyan-400 shrink-0" />
                <a href={`mailto:${data.email}`} className="hover:text-white transition-colors">
                  {data.email}
                </a>
              </div>
            )}
            {data.phone && (
              <div className="flex items-center gap-2 text-sm text-zinc-400">
                <Phone size={14} className="text-emerald-400 shrink-0" />
                {data.phone}
              </div>
            )}
          </div>
        </motion.div>

        {/* Philosophy cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            {
              emoji: "🎯",
              title: "Production First",
              desc: "Every system I build is designed to survive real traffic, real failures, and real users.",
            },
            {
              emoji: "🔬",
              title: "Test Everything",
              desc: "No code ships without tests. No exception. Reliability is engineered, not hoped for.",
            },
            {
              emoji: "🧠",
              title: "AI with Guardrails",
              desc: "LLMs hallucinate. My systems don't — because I build guardrails at every inference step.",
            },
            {
              emoji: "📦",
              title: "Minimal Magic",
              desc: "Clear intent, resilient failure, observable behavior. No black boxes in production.",
            },
          ].map((card, i) => (
            <motion.div
              key={card.title}
              className="glass rounded-2xl p-5 hover:border-white/15 transition-colors"
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.1 + i * 0.1, duration: 0.45 }}
            >
              <span className="text-2xl mb-3 block">{card.emoji}</span>
              <h4 className="text-white font-bold text-sm mb-1.5">{card.title}</h4>
              <p className="text-zinc-500 text-xs leading-relaxed">{card.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
