"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Mail, Github, Linkedin, ExternalLink, ArrowRight } from "lucide-react";
import { PortfolioData } from "@/lib/types";

export function Contact({ data }: { data: PortfolioData }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section id="contact" ref={ref} className="relative py-24 px-6">
      <div className="max-w-3xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
        >
          <div className="section-label justify-center">
            Get In Touch
          </div>
          <h2 className="text-4xl md:text-6xl font-black text-white mb-4">
            Let&apos;s Build
            <br />
            <span className="gradient-text">Something Real</span>
          </h2>
          <p className="text-zinc-400 text-lg mb-10 max-w-lg mx-auto">
            Open to Senior AI Engineer, Applied AI, and Founding Engineer roles.
            If you&apos;re building with LLMs and need production-grade work, let&apos;s talk.
          </p>
        </motion.div>

        {data.email && (
          <motion.a
            href={`mailto:${data.email}`}
            className="inline-flex items-center gap-3 px-8 py-4 rounded-2xl bg-gradient-to-r from-purple-600 to-purple-500 text-white font-bold text-lg hover:opacity-90 active:scale-95 transition-all shadow-2xl shadow-purple-500/20 mb-10"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={isInView ? { opacity: 1, scale: 1 } : {}}
            transition={{ delay: 0.15, duration: 0.45 }}
          >
            <Mail size={22} />
            {data.email}
            <ArrowRight size={18} />
          </motion.a>
        )}

        {/* Social links */}
        <motion.div
          className="flex items-center justify-center gap-4 flex-wrap"
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 0.25 }}
        >
          {data.github && (
            <a
              href={data.github}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl glass text-zinc-400 text-sm font-medium hover:text-white transition-colors"
            >
              <Github size={16} />
              GitHub
            </a>
          )}
          {data.linkedin && (
            <a
              href={data.linkedin}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl glass text-zinc-400 text-sm font-medium hover:text-white transition-colors"
            >
              <Linkedin size={16} />
              LinkedIn
            </a>
          )}
          {data.website && (
            <a
              href={data.website}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl glass text-zinc-400 text-sm font-medium hover:text-white transition-colors"
            >
              <ExternalLink size={16} />
              Website
            </a>
          )}
        </motion.div>

        {/* Footer */}
        <motion.p
          className="text-zinc-700 text-xs mt-16"
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 0.4 }}
        >
          Portfolio generated from CV · Built with Next.js + Claude AI
        </motion.p>
      </div>
    </section>
  );
}
