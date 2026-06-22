"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { FileText, Github, Linkedin, ExternalLink, ChevronDown } from "lucide-react";
import { PortfolioData } from "@/lib/types";

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};
const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: "easeOut" } },
};

function TypewriterTerminal({ items }: { items: string[] }) {
  const [text, setText] = useState("");
  const [idx, setIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!items.length) return;
    const current = items[idx % items.length];
    const speed = deleting ? 40 : 80;
    const timer = setTimeout(() => {
      if (!deleting) {
        setText(current.slice(0, charIdx + 1));
        if (charIdx + 1 === current.length) {
          setTimeout(() => setDeleting(true), 2000);
        } else {
          setCharIdx((c) => c + 1);
        }
      } else {
        setText(current.slice(0, charIdx - 1));
        if (charIdx - 1 === 0) {
          setDeleting(false);
          setIdx((i) => (i + 1) % items.length);
          setCharIdx(0);
        } else {
          setCharIdx((c) => c - 1);
        }
      }
    }, speed);
    return () => clearTimeout(timer);
  }, [text, idx, charIdx, deleting, items]);

  if (!items.length) return null;
  return (
    <div className="glass rounded-xl px-5 py-3 inline-flex items-center gap-2 text-sm font-mono max-w-full">
      <span className="text-purple-400 select-none">›</span>
      <span className="text-zinc-300 truncate">{text}</span>
      <span className="cursor" />
    </div>
  );
}

function TechStackCard({ skills }: { skills: PortfolioData["skills"] }) {
  const allSkills = [
    ...skills.languages.slice(0, 3),
    ...skills.frameworks.slice(0, 3),
    ...skills.aiml.slice(0, 3),
    ...skills.cloud.slice(0, 3),
  ].slice(0, 12);

  const totalTests = 0;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.92, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ delay: 0.8, duration: 0.6 }}
      className="glass rounded-2xl p-5 w-56"
    >
      <p className="text-[10px] font-bold tracking-widest text-zinc-500 uppercase mb-3">
        Tech Stack
      </p>
      <div className="grid grid-cols-4 gap-2 mb-3">
        {allSkills.map((s) => (
          <div
            key={s}
            title={s}
            className="w-9 h-9 rounded-lg bg-white/5 border border-white/8 flex items-center justify-center text-xs font-bold text-zinc-400 hover:text-white hover:border-purple-500/40 transition-colors cursor-default select-none"
          >
            {s.slice(0, 2)}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-1.5 text-[11px]">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-emerald-400 font-mono font-semibold">
          {skills.languages.length + skills.frameworks.length + skills.aiml.length + skills.cloud.length + skills.databases.length + skills.tools.length} skills
        </span>
        <span className="text-zinc-600">·</span>
        <span className="text-zinc-500">in stack</span>
      </div>
    </motion.div>
  );
}

function StatItem({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center sm:text-left">
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-[10px] font-semibold tracking-widest text-zinc-500 uppercase mt-0.5">
        {label}
      </p>
    </div>
  );
}

export function Hero({ data }: { data: PortfolioData }) {
  const typewriterItems = [
    ...data.projects.map((p) => p.name),
    ...data.skills.aiml.slice(0, 3),
  ].filter(Boolean);

  const stats = [
    {
      value: `${data.experience.reduce((a, e) => a + e.description.length, 0)}+`,
      label: "Achievements",
    },
    { value: `${data.projects.length}+`, label: "Projects Built" },
    { value: `${data.skills.aiml.length}+`, label: "AI Skills" },
    {
      value: `${data.experience.length * 2}+`,
      label: "Years Exp",
    },
  ];

  return (
    <section
      id="hero"
      className="relative min-h-screen flex items-center pt-20 pb-16 px-6"
    >
      <div className="max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        {/* Left */}
        <motion.div
          variants={stagger}
          initial="hidden"
          animate="show"
          className="flex flex-col gap-5"
        >
          {/* Badge */}
          <motion.div variants={fadeUp}>
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium bg-purple-500/10 text-purple-300 border border-purple-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Open to Senior AI Engineer Roles
            </span>
          </motion.div>

          {/* Name + Title */}
          <motion.div variants={fadeUp}>
            <h1 className="text-6xl md:text-7xl font-black leading-[1.05] tracking-tight">
              <span className="text-white block">{data.name.split(" ")[0]}</span>
              <span className="text-white block">{data.name.split(" ").slice(1).join(" ")}</span>
              <span className="gradient-text block mt-1">{data.title}</span>
            </h1>
          </motion.div>

          {/* Summary */}
          <motion.p
            variants={fadeUp}
            className="text-zinc-400 text-base leading-relaxed max-w-lg"
          >
            {data.summary}
          </motion.p>

          {/* Typewriter */}
          <motion.div variants={fadeUp}>
            <TypewriterTerminal items={typewriterItems} />
          </motion.div>

          {/* Stats row */}
          <motion.div
            variants={fadeUp}
            className="flex flex-wrap gap-x-8 gap-y-4 pt-2 border-t border-white/8"
          >
            {stats.map((s) => (
              <StatItem key={s.label} value={s.value} label={s.label} />
            ))}
          </motion.div>

          {/* CTAs */}
          <motion.div variants={fadeUp} className="flex flex-wrap items-center gap-3 pt-1">
            {data.email && (
              <a
                href={`mailto:${data.email}`}
                className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-gradient-to-r from-purple-600 to-purple-500 text-white text-sm font-semibold hover:opacity-90 transition-opacity"
              >
                <FileText size={15} />
                View Resume
              </a>
            )}
            {data.github && (
              <a
                href={data.github}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-5 py-2.5 rounded-full glass text-zinc-300 text-sm font-semibold hover:text-white transition-colors"
              >
                <Github size={15} />
                GitHub
              </a>
            )}
            {data.linkedin && (
              <a
                href={data.linkedin}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-5 py-2.5 rounded-full glass text-zinc-300 text-sm font-semibold hover:text-white transition-colors"
              >
                <Linkedin size={15} />
                LinkedIn
              </a>
            )}
            {data.website && (
              <a
                href={data.website}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-5 py-2.5 rounded-full glass text-zinc-300 text-sm font-semibold hover:text-white transition-colors"
              >
                <ExternalLink size={15} />
                Website
              </a>
            )}
          </motion.div>
        </motion.div>

        {/* Right */}
        <div className="flex flex-col items-center lg:items-end gap-6">
          {/* Profile photo placeholder */}
          <motion.div
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5, duration: 0.6 }}
            className="relative"
          >
            <div className="w-48 h-48 rounded-full bg-gradient-to-br from-purple-600 to-cyan-500 p-[3px]">
              <div className="w-full h-full rounded-full bg-[#0d0d1f] flex items-center justify-center overflow-hidden">
                <span className="text-5xl font-black gradient-text select-none">
                  {data.name
                    .split(" ")
                    .slice(0, 2)
                    .map((w) => w[0])
                    .join("")}
                </span>
              </div>
            </div>
            <div className="absolute -bottom-2 -right-2 w-6 h-6 rounded-full bg-emerald-400 border-2 border-[#0a0a1a]" />
          </motion.div>

          {/* Tech Stack Card */}
          <TechStackCard skills={data.skills} />
        </div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1"
        animate={{ y: [0, 6, 0] }}
        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
      >
        <span className="text-[10px] text-zinc-600 tracking-widest uppercase">Scroll</span>
        <ChevronDown size={16} className="text-zinc-600" />
      </motion.div>
    </section>
  );
}
