import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { ask, getBriefings } from "../api";
import { VoiceOrb } from "../components/VoiceOrb";
import { BriefingCard } from "../components/BriefingCard";
import { useVoice } from "../hooks/useVoice";
import { writeReminderToCalendar } from "../lib/calendar";
import { speak, stopSpeaking } from "../lib/tts";
import { colors, fonts } from "../theme";
import type { Briefing } from "../types";
import { updateReminder } from "../api";

interface Props {
  /** Increments each time a sarathi://listen deep link arrives (Siri). */
  listenSignal: number;
  onReminderSaved: () => void;
}

export function HomeScreen({ listenSignal, onReminderSaved }: Props) {
  const [briefings, setBriefings] = useState<Briefing[]>([]);
  const [loading, setLoading] = useState(true);
  const [speaking, setSpeaking] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const listRef = useRef<FlatList<Briefing>>(null);

  const handleFinalTranscript = useCallback(async (transcript: string) => {
    try {
      const res = await ask(transcript);

      // Optimistically add the new briefing to the top of the feed.
      const briefing: Briefing = {
        id: res.briefing_id,
        query: transcript,
        type: res.type,
        spoken: res.spoken,
        detail: res.detail,
        sources: res.sources,
        reminder_id: res.reminder_id,
        created_at: new Date().toISOString(),
      };
      setBriefings((prev) => [briefing, ...prev]);
      listRef.current?.scrollToOffset({ offset: 0, animated: true });

      // Reminder → native calendar, then remember the event id server-side.
      if (res.reminder && res.reminder_id) {
        const eventId = await writeReminderToCalendar(res.reminder).catch(() => null);
        if (eventId) {
          updateReminder(res.reminder_id, { calendar_event_id: eventId }).catch(() => {});
          setBanner("Reminder saved to your calendar ◷");
        } else {
          setBanner("Reminder saved ◷");
        }
        onReminderSaved();
        setTimeout(() => setBanner(null), 3500);
      }

      setSpeaking(true);
      await speak(res.spoken, () => setSpeaking(false));
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Something went wrong";
      setBanner(msg);
      setTimeout(() => setBanner(null), 5000);
    } finally {
      voice.done();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const voice = useVoice({ onFinalTranscript: handleFinalTranscript });

  useEffect(() => {
    getBriefings()
      .then(setBriefings)
      .catch((e) => setBanner(e instanceof Error ? e.message : "Could not load history"))
      .finally(() => setLoading(false));
  }, []);

  // Siri deep link → start listening.
  useEffect(() => {
    if (listenSignal > 0 && voice.state === "idle") {
      stopSpeaking();
      voice.start();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listenSignal]);

  const onOrbPress = () => {
    if (voice.state === "idle") {
      stopSpeaking();
      setSpeaking(false);
      voice.start();
    } else if (voice.state === "listening") {
      voice.stop();
    }
  };

  const statusLine =
    voice.state === "listening"
      ? voice.partial || "Listening…"
      : voice.state === "processing"
        ? "Sarathi is working on it…"
        : speaking
          ? "Speaking — tap the orb to interrupt"
          : "Tap the orb and speak";

  return (
    <View style={styles.container}>
      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.brass} />
        </View>
      ) : briefings.length === 0 ? (
        <View style={styles.center}>
          <Text style={styles.emptyTitle}>Namaste.</Text>
          <Text style={styles.emptyBody}>
            Ask about today's headlines, prep for a speech, or say{" "}
            <Text style={{ fontFamily: fonts.displayItalic }}>
              “remind me to call the district office at 5pm.”
            </Text>
          </Text>
        </View>
      ) : (
        <FlatList
          ref={listRef}
          data={briefings}
          keyExtractor={(b) => b.id}
          renderItem={({ item }) => (
            <BriefingCard
              briefing={item}
              onSpeak={(t) => {
                setSpeaking(true);
                speak(t, () => setSpeaking(false));
              }}
            />
          )}
          contentContainerStyle={{ paddingTop: 12, paddingBottom: 190 }}
          showsVerticalScrollIndicator={false}
        />
      )}

      {banner && (
        <View style={styles.banner}>
          <Text style={styles.bannerText} numberOfLines={3}>
            {banner}
          </Text>
        </View>
      )}
      {voice.error && (
        <View style={styles.banner}>
          <Text style={styles.bannerText}>{voice.error}</Text>
        </View>
      )}

      <View style={styles.dock} pointerEvents="box-none">
        <Text style={styles.status} numberOfLines={2}>
          {statusLine}
        </Text>
        <VoiceOrb state={voice.state} onPress={onOrbPress} />
        {speaking && (
          <Pressable
            onPress={() => {
              stopSpeaking();
              setSpeaking(false);
            }}
          >
            <Text style={styles.stopSpeech}>■ stop speaking</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 36 },
  emptyTitle: {
    fontFamily: fonts.display,
    fontSize: 34,
    color: colors.parchment,
    marginBottom: 12,
  },
  emptyBody: {
    fontFamily: fonts.body,
    fontSize: 15,
    lineHeight: 23,
    color: colors.parchmentDim,
    textAlign: "center",
  },
  dock: {
    position: "absolute",
    bottom: 24,
    left: 0,
    right: 0,
    alignItems: "center",
    gap: 14,
  },
  status: {
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
    color: colors.parchmentDim,
    textAlign: "center",
    paddingHorizontal: 48,
  },
  stopSpeech: {
    fontFamily: fonts.bodySemi,
    fontSize: 12,
    letterSpacing: 1,
    color: colors.brassBright,
    textTransform: "uppercase",
  },
  banner: {
    position: "absolute",
    top: 8,
    left: 16,
    right: 16,
    backgroundColor: colors.inkRaised2,
    borderColor: colors.hairline,
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
  },
  bannerText: {
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
    color: colors.parchment,
    textAlign: "center",
  },
});
