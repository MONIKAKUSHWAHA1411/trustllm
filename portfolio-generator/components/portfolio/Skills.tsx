"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { PortfolioSkills } from "@/lib/types";

const BAR_COLORS = [
  "from-purple-600 to-purple-400",
  "from-cyan-600 to-cyan-300",
  "from-yellow-600 to-yellow-300",
  "from-emerald-600 to-emerald-400",
  "from-red-600 to-red-400",
  "from-blue-600 to-blue-400",
];

const SKILL_PERCENTAGES: Record<string, number> = {
  Python: 97,
  LangGraph: 92,
  FastAPI: 95,
  Angular: 88,
  TypeScript: 90,
  Java: 85,
  React: 82,
  "Spring Boot": 87,
  Docker: 89,
  AWS: 84,
  "Node.js": 83,
  PostgreSQL: 86,
};

function getPercent(skill: string): number {
  return (
    SKILL_PERCENTAGES[skill] ||
    Math.floor(Math.random() * 20 + 70)
  );
}

interface SkillBarProps {
  name: string;
  pct: number;
  color: string;
  delay: number;
  isInView: boolean;
  subtitle?: string;
}

function SkillBar({ name, pct, color, delay, isInView, subtitle }: SkillBarProps) {
  return (
    <div className="py-3 border-b border-white/5 last:border-0">
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-7 h-7 rounded-lg bg-gradient-to-br ${color} flex items-center justify-center text-xs font-black text-white select-none`}>
          {name.slice(0, 1)}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <span className="text-white text-sm font-semibold">{name}</span>
            <span className={`text-sm font-bold bg-gradient-to-r ${color} bg-clip-text text-transparent`}>
              {pct}%
            </span>
          </div>
          {subtitle && (
            <p className="text-zinc-600 text-xs italic mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>
      <div className="h-1.5 rounded-full bg-white/5 overflow-hidden ml-10">
        <motion.div
          className={`h-full rounded-full bg-gradient-to-r ${color}`}
          initial={{ width: 0 }}
          animate={isInView ? { width: `${pct}%` } : { width: 0 }}
          transition={{ delay: delay + 0.2, duration: 0.9, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

const CATEGORIES = [
  {
    key: "aiml" as keyof PortfolioSkills,
    label: "AI & LLM Engineering",
    color: "from-purple-600 to-purple-400",
  },
  {
    key: "databases" as keyof PortfolioSkills,
    label: "Retrieval & Memory",
    color: "from-cyan-600 to-cyan-400",
  },
  {
    key: "frameworks" as keyof PortfolioSkills,
    label: "Backend & APIs",
    color: "from-emerald-600 to-emerald-400",
  },
  {
    key: "cloud" as keyof PortfolioSkills,
    label: "Cloud & DevOps",
    color: "from-blue-600 to-blue-400",
  },
  {
    key: "languages" as keyof PortfolioSkills,
    label: "Languages",
    color: "from-yellow-600 to-yellow-400",
  },
  {
    key: "tools" as keyof PortfolioSkills,
    label: "Tools & Platforms",
    color: "from-pink-600 to-pink-400",
  },
];

function CategoryCard({
  label,
  color,
  skills,
  delay,
  isInView,
}: {
  label: string;
  color: string;
  skills: string[];
  delay: number;
  isInView: boolean;
}) {
  if (!skills.length) return null;
  return (
    <motion.div
      className="glass rounded-2xl p-5"
      initial={{ opacity: 0, y: 20 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ delay, duration: 0.5 }}
    >
      <div className="flex items-center gap-2 mb-4">
        <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${color} flex items-center justify-center`}>
          <span className="text-white text-xs font-black">{label.slice(0, 2).toUpperCase()}</span>
        </div>
        <h4 className={`text-sm font-bold bg-gradient-to-r ${color} bg-clip-text text-transparent`}>
          {label}
        </h4>
      </div>
      <div className="flex flex-wrap gap-2">
        {skills.map((s) => (
          <span key={s} className="tag-neutral tag text-xs">
            {s}
          </span>
        ))}
      </div>
    </motion.div>
  );
}

const SKILL_SUBTITLES: Record<string, string> = {
  Python: "Breathing it since day one",
  LangGraph: "State machine poet ✨",
  FastAPI: "Auto-docs everything 📋",
  Angular: "Signals believer since v17",
  "Hybrid RAG": "FAISS + BM25 + HyDE + CRAG",
  TypeScript: "Type everything, always",
};

export function Skills({ skills }: { skills: PortfolioSkills }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  const topSkills = [
    ...skills.aiml.slice(0, 2),
    ...skills.frameworks.slice(0, 2),
    ...skills.languages.slice(0, 1),
  ].slice(0, 5);

  return (
    <section id="skills" ref={ref} className="relative py-24 px-6">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
        >
          <div className="section-label">Technical Depth</div>
          <h2 className="text-4xl md:text-5xl font-black text-white mb-3">
            What I Engineer
          </h2>
          <p className="text-zinc-400 max-w-lg mb-12">
            Full-stack AI — from embedding models to production UIs — with
            guardrails at every layer.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-10">
          {/* Skill bars */}
          <motion.div
            className="glass rounded-2xl p-6"
            initial={{ opacity: 0, x: -20 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.5 }}
          >
            {topSkills.map((skill, i) => (
              <SkillBar
                key={skill}
                name={skill}
                pct={getPercent(skill)}
                color={BAR_COLORS[i % BAR_COLORS.length]}
                delay={i * 0.1}
                isInView={isInView}
                subtitle={SKILL_SUBTITLES[skill]}
              />
            ))}
          </motion.div>

          {/* Primary category */}
          <div className="flex flex-col gap-4">
            {CATEGORIES.slice(0, 2).map((cat, i) => (
              <CategoryCard
                key={cat.key}
                label={cat.label}
                color={cat.color}
                skills={skills[cat.key] as string[]}
                delay={0.2 + i * 0.1}
                isInView={isInView}
              />
            ))}
          </div>
        </div>

        {/* Other categories */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {CATEGORIES.slice(2).map((cat, i) => (
            <CategoryCard
              key={cat.key}
              label={cat.label}
              color={cat.color}
              skills={skills[cat.key] as string[]}
              delay={0.4 + i * 0.08}
              isInView={isInView}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
