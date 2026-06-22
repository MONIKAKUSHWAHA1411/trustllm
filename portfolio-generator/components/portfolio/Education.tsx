"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { GraduationCap } from "lucide-react";
import { PortfolioEducation } from "@/lib/types";

export function Education({ education }: { education: PortfolioEducation[] }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  if (!education.length) return null;

  return (
    <section id="education" ref={ref} className="relative py-16 px-6">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
        >
          <div className="section-label">Academic</div>
          <h2 className="text-3xl md:text-4xl font-black text-white mb-10">
            Education
          </h2>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {education.map((edu, i) => (
            <motion.div
              key={`${edu.institution}-${i}`}
              className="glass rounded-2xl p-6 hover:border-white/15 transition-colors"
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: i * 0.1, duration: 0.5 }}
            >
              <div className="flex items-start gap-4">
                <div className="w-11 h-11 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0">
                  <GraduationCap size={20} className="text-cyan-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white font-bold leading-tight">{edu.degree}</p>
                  <p className="text-cyan-400 font-semibold text-sm mt-1">
                    {edu.institution}
                  </p>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-xs text-zinc-500 font-mono">
                      {edu.startDate} – {edu.endDate}
                    </span>
                    {edu.grade && (
                      <>
                        <span className="text-zinc-700">·</span>
                        <span className="text-xs text-emerald-400 font-semibold">
                          {edu.grade}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
