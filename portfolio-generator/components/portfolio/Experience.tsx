"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { PortfolioExperience } from "@/lib/types";

export function Experience({ experience }: { experience: PortfolioExperience[] }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  if (!experience.length) return null;

  return (
    <section id="experience" ref={ref} className="relative py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
        >
          <div className="section-label">Career</div>
          <h2 className="text-4xl md:text-5xl font-black text-white mb-12">
            Experience
          </h2>
        </motion.div>

        <div className="timeline-track space-y-10">
          {experience.map((exp, i) => (
            <motion.div
              key={`${exp.company}-${i}`}
              className="relative"
              initial={{ opacity: 0, x: -20 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ delay: i * 0.12, duration: 0.5 }}
            >
              <div className="timeline-dot" />

              <div className="glass rounded-2xl p-6 hover:border-white/15 transition-colors">
                {/* Header */}
                <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-white">{exp.role}</h3>
                    <p className="text-purple-400 font-semibold text-sm mt-0.5">
                      {exp.company}
                    </p>
                    {exp.location && (
                      <p className="text-zinc-600 text-xs mt-0.5">{exp.location}</p>
                    )}
                  </div>
                  <span className="flex items-center gap-1.5 text-xs font-mono text-zinc-500 bg-white/5 px-3 py-1.5 rounded-lg border border-white/8 shrink-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                    {exp.startDate} — {exp.endDate}
                  </span>
                </div>

                {/* Bullets */}
                <ul className="space-y-2">
                  {exp.description.map((bullet, j) => (
                    <li key={j} className="flex items-start gap-3 text-sm text-zinc-400">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-purple-500/60 shrink-0" />
                      <span className="leading-relaxed">{bullet}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
