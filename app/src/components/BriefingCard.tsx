import React from "react";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { colors, fonts, typeMeta } from "../theme";
import type { Briefing } from "../types";

interface Props {
  briefing: Briefing;
  onSpeak: (text: string) => void;
}

function timeAgo(iso: string): string {
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export function BriefingCard({ briefing, onSpeak }: Props) {
  const meta = typeMeta[briefing.type] ?? typeMeta.GENERAL;

  return (
    <View style={[styles.card, { borderLeftColor: meta.accent }]}>
      <View style={styles.header}>
        <View style={[styles.chip, { borderColor: meta.accent }]}>
          <Text style={[styles.chipGlyph, { color: meta.accent }]}>{meta.glyph}</Text>
          <Text style={[styles.chipText, { color: meta.accent }]}>{meta.label}</Text>
        </View>
        <Text style={styles.time}>{timeAgo(briefing.created_at)}</Text>
      </View>

      <Text style={styles.query}>“{briefing.query}”</Text>
      <Text style={styles.spoken}>{briefing.spoken}</Text>
      {briefing.detail ? <Text style={styles.detail}>{briefing.detail}</Text> : null}

      {briefing.sources.length > 0 && (
        <View style={styles.sources}>
          {briefing.sources.slice(0, 4).map((s, i) => (
            <Pressable
              key={`${s.url}-${i}`}
              onPress={() => Linking.openURL(s.url).catch(() => {})}
              style={styles.sourceRow}
            >
              <Text style={styles.sourceBullet}>↗</Text>
              <Text style={styles.sourceText} numberOfLines={1}>
                {s.title || s.url}
              </Text>
            </Pressable>
          ))}
        </View>
      )}

      <Pressable style={styles.speakBtn} onPress={() => onSpeak(briefing.spoken)}>
        <Text style={styles.speakBtnText}>▷ Speak</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.inkRaised,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.hairline,
    borderLeftWidth: 3,
    padding: 18,
    marginHorizontal: 16,
    marginBottom: 14,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  chipGlyph: { fontSize: 11 },
  chipText: {
    fontFamily: fonts.bodySemi,
    fontSize: 11,
    letterSpacing: 1.2,
    textTransform: "uppercase",
  },
  time: { fontFamily: fonts.body, fontSize: 12, color: colors.parchmentFaint },
  query: {
    fontFamily: fonts.displayItalic,
    fontSize: 13,
    color: colors.parchmentDim,
    marginBottom: 8,
  },
  spoken: {
    fontFamily: fonts.display,
    fontSize: 18,
    lineHeight: 26,
    color: colors.parchment,
  },
  detail: {
    fontFamily: fonts.body,
    fontSize: 14,
    lineHeight: 21,
    color: colors.parchmentDim,
    marginTop: 10,
  },
  sources: {
    marginTop: 14,
    borderTopWidth: 1,
    borderTopColor: colors.hairline,
    paddingTop: 10,
    gap: 6,
  },
  sourceRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  sourceBullet: { color: colors.brass, fontSize: 12 },
  sourceText: {
    flex: 1,
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
    color: colors.brassBright,
  },
  speakBtn: { alignSelf: "flex-start", marginTop: 14 },
  speakBtnText: {
    fontFamily: fonts.bodySemi,
    fontSize: 12,
    letterSpacing: 1,
    color: colors.parchmentDim,
    textTransform: "uppercase",
  },
});
