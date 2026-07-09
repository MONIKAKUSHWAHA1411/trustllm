// SARATHI visual language — ink-navy ground, brass-gold accent.
// Display type: Fraunces. Body: IBM Plex Sans.

export const colors = {
  // grounds
  ink: "#0B1524", // deepest navy — app background
  inkRaised: "#122036", // cards
  inkRaised2: "#18294A", // pressed / secondary surfaces
  hairline: "rgba(201, 168, 76, 0.16)", // brass hairline borders

  // brass
  brass: "#C9A84C",
  brassBright: "#E8C96A",
  brassDeep: "#8C6F2A",

  // text
  parchment: "#F3EBD8", // primary text
  parchmentDim: "rgba(243, 235, 216, 0.62)",
  parchmentFaint: "rgba(243, 235, 216, 0.38)",

  // briefing-type accents (kept inside the navy/brass world)
  media: "#D98E73", // terracotta — media watch
  speech: "#9CC5A1", // sage — speech prep
  reminder: "#E8C96A", // brass — reminders
  general: "#8FA9C9", // steel blue — general

  danger: "#D9827B",
} as const;

export type BriefingType = "REMINDER" | "MEDIA_WATCH" | "SPEECH_PREP" | "GENERAL";

export const typeMeta: Record<BriefingType, { label: string; accent: string; glyph: string }> = {
  REMINDER: { label: "Reminder", accent: colors.reminder, glyph: "◷" },
  MEDIA_WATCH: { label: "Media Watch", accent: colors.media, glyph: "◉" },
  SPEECH_PREP: { label: "Speech Prep", accent: colors.speech, glyph: "❝" },
  GENERAL: { label: "Briefing", accent: colors.general, glyph: "✦" },
};

export const fonts = {
  display: "Fraunces_600SemiBold",
  displayItalic: "Fraunces_500Medium_Italic",
  body: "IBMPlexSans_400Regular",
  bodyMedium: "IBMPlexSans_500Medium",
  bodySemi: "IBMPlexSans_600SemiBold",
} as const;
