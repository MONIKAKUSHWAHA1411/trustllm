"use client";

import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileText,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  X,
} from "lucide-react";
import { PortfolioData } from "@/lib/types";

type UploadState = "idle" | "dragging" | "selected" | "parsing" | "error";

export default function HomePage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string>("");

  const handleFile = (f: File) => {
    const allowed = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "application/msword",
    ];
    const byExt =
      f.name.endsWith(".pdf") || f.name.endsWith(".docx") || f.name.endsWith(".doc");

    if (!allowed.includes(f.type) && !byExt) {
      setError("Please upload a PDF or Word document (.pdf, .docx, .doc)");
      setState("error");
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError("File size must be under 10 MB");
      setState("error");
      return;
    }
    setFile(f);
    setState("selected");
    setError("");
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setState("idle");
    const dropped = e.dataTransfer.files[0];
    if (dropped) handleFile(dropped);
  }, []);

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setState("dragging");
  };

  const onDragLeave = () => setState("idle");

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  };

  const generate = async () => {
    if (!file) return;
    setState("parsing");
    setError("");

    try {
      const fd = new FormData();
      fd.append("cv", file);

      const res = await fetch("/api/parse-cv", { method: "POST", body: fd });
      const json = await res.json();

      if (!res.ok || json.error) {
        throw new Error(json.error || "Parsing failed");
      }

      const data: PortfolioData = json.data;
      sessionStorage.setItem("portfolio_data", JSON.stringify(data));
      router.push("/portfolio");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setState("error");
    }
  };

  const reset = () => {
    setFile(null);
    setState("idle");
    setError("");
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <main className="min-h-screen bg-[#050505] flex flex-col items-center justify-center px-4 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-dots pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(34,211,238,0.08),transparent)] pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_80%_80%,rgba(168,85,247,0.06),transparent)] pointer-events-none" />

      <div className="relative z-10 w-full max-w-2xl">
        {/* Header */}
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 mb-6">
            <Sparkles size={12} />
            Powered by Claude AI
          </div>
          <h1 className="text-5xl md:text-6xl font-bold mb-4">
            <span className="text-white">Your CV,</span>
            <br />
            <span className="gradient-text">Reimagined.</span>
          </h1>
          <p className="text-zinc-400 text-lg max-w-md mx-auto leading-relaxed">
            Upload your CV and get a stunning, animated portfolio website in seconds.
          </p>
        </motion.div>

        {/* Upload area */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
        >
          <AnimatePresence mode="wait">
            {state === "parsing" ? (
              <ParsingState key="parsing" />
            ) : (
              <motion.div
                key="upload"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <div
                  onDrop={onDrop}
                  onDragOver={onDragOver}
                  onDragLeave={onDragLeave}
                  onClick={() => state !== "selected" && inputRef.current?.click()}
                  className={`
                    relative rounded-2xl border-2 border-dashed p-10 text-center cursor-pointer
                    transition-all duration-300
                    ${
                      state === "dragging"
                        ? "border-cyan-400 bg-cyan-500/5 scale-[1.01]"
                        : state === "selected"
                        ? "border-emerald-500/50 bg-emerald-500/5 cursor-default"
                        : state === "error"
                        ? "border-red-500/50 bg-red-500/5"
                        : "border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]"
                    }
                  `}
                >
                  <input
                    ref={inputRef}
                    type="file"
                    accept=".pdf,.doc,.docx"
                    onChange={onInputChange}
                    className="hidden"
                  />

                  <AnimatePresence mode="wait">
                    {state === "selected" && file ? (
                      <motion.div
                        key="selected"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="flex flex-col items-center gap-3"
                      >
                        <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
                          <CheckCircle2 className="text-emerald-400" size={28} />
                        </div>
                        <div>
                          <p className="text-white font-medium text-lg">{file.name}</p>
                          <p className="text-zinc-500 text-sm mt-1">
                            {(file.size / 1024).toFixed(0)} KB · Ready to generate
                          </p>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            reset();
                          }}
                          className="mt-2 text-zinc-500 hover:text-zinc-300 transition-colors text-sm flex items-center gap-1"
                        >
                          <X size={14} /> Remove file
                        </button>
                      </motion.div>
                    ) : state === "error" ? (
                      <motion.div
                        key="error"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex flex-col items-center gap-3"
                      >
                        <AlertCircle className="text-red-400" size={40} />
                        <p className="text-red-400 font-medium">{error}</p>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            reset();
                            inputRef.current?.click();
                          }}
                          className="text-zinc-400 hover:text-white text-sm transition-colors"
                        >
                          Try again
                        </button>
                      </motion.div>
                    ) : (
                      <motion.div
                        key="idle"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex flex-col items-center gap-4"
                      >
                        <motion.div
                          animate={
                            state === "dragging"
                              ? { scale: 1.1, rotate: 5 }
                              : { scale: 1, rotate: 0 }
                          }
                          className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center"
                        >
                          <Upload
                            className={state === "dragging" ? "text-cyan-400" : "text-zinc-400"}
                            size={28}
                          />
                        </motion.div>
                        <div>
                          <p className="text-white font-medium text-lg">
                            {state === "dragging"
                              ? "Drop it here!"
                              : "Drop your CV here"}
                          </p>
                          <p className="text-zinc-500 text-sm mt-1">
                            or{" "}
                            <span className="text-cyan-400 hover:text-cyan-300 transition-colors">
                              browse files
                            </span>{" "}
                            · PDF or DOCX · Max 10 MB
                          </p>
                        </div>
                        <div className="flex items-center gap-4 mt-2">
                          {["PDF", "DOCX", "DOC"].map((ext) => (
                            <span
                              key={ext}
                              className="flex items-center gap-1.5 text-xs text-zinc-500"
                            >
                              <FileText size={12} />
                              {ext}
                            </span>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Generate button */}
                <AnimatePresence>
                  {state === "selected" && (
                    <motion.button
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      onClick={generate}
                      className="mt-4 w-full py-4 rounded-xl bg-gradient-to-r from-cyan-500 to-purple-600 text-white font-semibold text-lg flex items-center justify-center gap-2 hover:opacity-90 active:scale-[0.99] transition-all duration-200 shadow-lg shadow-cyan-500/20"
                    >
                      <Sparkles size={20} />
                      Generate My Portfolio
                      <ArrowRight size={20} />
                    </motion.button>
                  )}
                </AnimatePresence>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Feature pills */}
        <motion.div
          className="flex flex-wrap justify-center gap-3 mt-10"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          {[
            "✨ Animated sections",
            "🎨 Dark AI aesthetic",
            "📱 Mobile responsive",
            "⚡ Instant generation",
            "🔒 Privacy first",
          ].map((pill) => (
            <span
              key={pill}
              className="px-3 py-1.5 rounded-full text-xs text-zinc-400 border border-white/8 bg-white/[0.02]"
            >
              {pill}
            </span>
          ))}
        </motion.div>
      </div>
    </main>
  );
}

function ParsingState() {
  const steps = [
    "Reading your CV...",
    "Extracting experience & skills...",
    "Crafting your narrative...",
    "Building your portfolio...",
  ];
  const [stepIdx] = useState(0);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="rounded-2xl border border-white/10 bg-white/[0.02] p-10 flex flex-col items-center gap-6"
    >
      {/* Spinner */}
      <div className="relative w-20 h-20">
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-transparent border-t-cyan-400 border-r-cyan-400"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        />
        <motion.div
          className="absolute inset-3 rounded-full border-2 border-transparent border-b-purple-500 border-l-purple-500"
          animate={{ rotate: -360 }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <Sparkles className="text-cyan-400" size={24} />
        </div>
      </div>

      <div className="text-center">
        <p className="text-white font-semibold text-lg mb-1">
          Generating your portfolio
        </p>
        <motion.p
          key={stepIdx}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-zinc-400 text-sm"
        >
          {steps[stepIdx]}
        </motion.p>
      </div>

      <div className="flex gap-1.5">
        {steps.map((_, i) => (
          <motion.div
            key={i}
            className={`h-1 rounded-full transition-all duration-500 ${
              i <= stepIdx ? "w-8 bg-cyan-400" : "w-2 bg-zinc-700"
            }`}
          />
        ))}
      </div>
    </motion.div>
  );
}
