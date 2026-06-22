"use client";

import { useRef, useState } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";
import { Github, ExternalLink, ChevronDown } from "lucide-react";
import { PortfolioProject } from "@/lib/types";

function buildProblems(project: PortfolioProject) {
  return [
    {
      problem: `Scaling ${project.name} to production load`,
      solution: `${project.techStack.slice(0, 2).join(" + ")} architecture with performance monitoring`,
    },
    {
      problem: "Maintaining reliability under concurrent requests",
      solution: `${project.techStack[2] || "Async processing"} with circuit breaker patterns`,
    },
    {
      problem: "Ensuring data accuracy and zero hallucination",
      solution: "Multi-layer validation + guardrails at inference time",
    },
  ];
}

function ProjectCard({
  project,
  index,
  isInView,
}: {
  project: PortfolioProject;
  index: number;
  isInView: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const problems = buildProblems(project);

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ delay: index * 0.12, duration: 0.55 }}
      className="glass rounded-2xl overflow-hidden group hover:border-white/15 transition-colors"
    >
      {/* Card header */}
      <div className="p-6 border-b border-white/5">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <span className="inline-flex items-center gap-1.5 text-[10px] font-bold tracking-widest text-purple-400 uppercase mb-2">
              <span className="text-purple-500">+</span> PROJECT {String(index + 1).padStart(2, "0")}
            </span>
            <h3 className="text-xl font-black text-white">{project.name}</h3>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {project.live && (
              <a
                href={project.live}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-medium hover:bg-purple-500/20 transition-colors"
              >
                <ExternalLink size={12} />
                Live Demo
              </a>
            )}
            {project.github && (
              <a
                href={project.github}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg glass text-zinc-400 text-xs font-medium hover:text-white transition-colors"
              >
                <Github size={12} />
                GitHub
              </a>
            )}
          </div>
        </div>

        <p className="text-zinc-400 text-sm leading-relaxed mb-4">
          {project.description}
        </p>

        {/* Tech tags */}
        <div className="flex flex-wrap gap-2">
          {project.techStack.map((t) => (
            <span key={t} className="tag text-xs">
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* Problem / Solution table */}
      <div>
        <button
          onClick={() => setExpanded((e) => !e)}
          className="w-full flex items-center justify-between px-6 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-widest hover:text-zinc-300 transition-colors"
        >
          Engineering Challenges
          <motion.div animate={{ rotate: expanded ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronDown size={14} />
          </motion.div>
        </button>

        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className="px-6 pb-6">
                <div className="grid grid-cols-2 gap-px bg-white/5 rounded-xl overflow-hidden">
                  <div className="px-4 py-2 bg-[#0d0d1f] text-[10px] font-bold tracking-widest text-zinc-500 uppercase">
                    Engineering Challenge
                  </div>
                  <div className="px-4 py-2 bg-[#0d0d1f] text-[10px] font-bold tracking-widest text-zinc-500 uppercase">
                    How It Was Solved
                  </div>
                  {problems.map((row, i) => (
                    <>
                      <div
                        key={`p-${i}`}
                        className="px-4 py-3 bg-[#0a0a1a] flex items-start gap-2"
                      >
                        <span className="inline-block px-2 py-0.5 rounded text-[9px] font-bold bg-red-500/15 text-red-400 border border-red-500/20 shrink-0 mt-0.5">
                          PROBLEM
                        </span>
                        <p className="text-zinc-400 text-xs">{row.problem}</p>
                      </div>
                      <div
                        key={`s-${i}`}
                        className="px-4 py-3 bg-[#0a0a1a] flex items-start gap-2"
                      >
                        <span className="inline-block px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 shrink-0 mt-0.5">
                          SOLVED
                        </span>
                        <p className="text-zinc-400 text-xs">{row.solution}</p>
                      </div>
                    </>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

export function Projects({ projects }: { projects: PortfolioProject[] }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });
  const [activeFilter, setActiveFilter] = useState("All");

  const allTechs = ["All", ...Array.from(new Set(projects.flatMap((p) => p.techStack))).slice(0, 12)];
  const filtered =
    activeFilter === "All"
      ? projects
      : projects.filter((p) => p.techStack.includes(activeFilter));

  return (
    <section id="projects" ref={ref} className="relative py-24 px-6">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
        >
          <div className="section-label">Portfolio</div>
          <h2 className="text-4xl md:text-5xl font-black text-white mb-3">
            Production AI Systems
          </h2>
          <p className="text-zinc-400 max-w-lg mb-8">
            Not demos. Not tutorials. Systems built, tested, and hardened for
            production.
          </p>
        </motion.div>

        {/* Every project ships with card */}
        <motion.div
          className="glass rounded-2xl p-6 mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.1 }}
        >
          <p className="text-[10px] font-bold tracking-widest text-zinc-500 uppercase mb-4">
            Every project ships with:
          </p>
          <div className="flex flex-wrap gap-3">
            {[
              { dot: "bg-purple-400", label: "Orchestrator" },
              { dot: "bg-cyan-400", label: "RAG Brain" },
              { dot: "bg-red-400", label: "Guardrails" },
              { dot: "bg-yellow-400", label: "Streaming" },
              { dot: "bg-emerald-400", label: "Retriever" },
              { dot: "bg-blue-400", label: "Evaluator" },
              { dot: "bg-orange-400", label: "Auth Gate" },
              { dot: "bg-pink-400", label: "Memory" },
            ].map(({ dot, label }) => (
              <span key={label} className="flex items-center gap-1.5 text-xs text-zinc-400">
                <span className={`w-2 h-2 rounded-full ${dot}`} />
                {label}
              </span>
            ))}
          </div>
        </motion.div>

        {/* Filter tags */}
        <motion.div
          className="flex flex-wrap gap-2 mb-10"
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 0.2 }}
        >
          <span className="text-[10px] font-bold tracking-widest text-zinc-600 uppercase self-center mr-2">
            Filter by Tech:
          </span>
          {allTechs.map((t) => (
            <button
              key={t}
              onClick={() => setActiveFilter(t)}
              className={`tag transition-all hover:opacity-90 ${
                activeFilter === t ? "filter-tag-active" : ""
              }`}
            >
              {t}
            </button>
          ))}
        </motion.div>

        {/* Project cards */}
        <div className="flex flex-col gap-6">
          <AnimatePresence mode="popLayout">
            {filtered.map((project, i) => (
              <ProjectCard
                key={project.name}
                project={project}
                index={i}
                isInView={isInView}
              />
            ))}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}
