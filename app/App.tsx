import React, { useEffect, useState } from "react";
import { Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import * as Linking from "expo-linking";
import { useFonts } from "expo-font";
import {
  Fraunces_500Medium_Italic,
  Fraunces_600SemiBold,
} from "@expo-google-fonts/fraunces";
import {
  IBMPlexSans_400Regular,
  IBMPlexSans_500Medium,
  IBMPlexSans_600SemiBold,
} from "@expo-google-fonts/ibm-plex-sans";
import { HomeScreen } from "./src/screens/HomeScreen";
import { RemindersScreen } from "./src/screens/RemindersScreen";
import { colors, fonts } from "./src/theme";

type Tab = "briefings" | "reminders";

export default function App() {
  const [fontsLoaded] = useFonts({
    Fraunces_600SemiBold,
    Fraunces_500Medium_Italic,
    IBMPlexSans_400Regular,
    IBMPlexSans_500Medium,
    IBMPlexSans_600SemiBold,
  });

  const [tab, setTab] = useState<Tab>("briefings");
  const [listenSignal, setListenSignal] = useState(0);
  const [reminderSignal, setReminderSignal] = useState(0);
  const url = Linking.useURL();

  // "Hey Siri, ask Sarathi" → Shortcut opens sarathi://listen →
  // we land on the briefing tab with the orb already listening.
  useEffect(() => {
    if (!url) return;
    const { hostname, path } = Linking.parse(url);
    if (hostname === "listen" || path === "listen") {
      setTab("briefings");
      setListenSignal((n) => n + 1);
    }
  }, [url]);

  if (!fontsLoaded) {
    return <View style={{ flex: 1, backgroundColor: colors.ink }} />;
  }

  return (
    <SafeAreaView style={styles.root}>
      <StatusBar style="light" />
      <View style={styles.header}>
        <Text style={styles.wordmark}>SARATHI</Text>
        <Text style={styles.tagline}>your chief of staff</Text>
      </View>

      <View style={styles.tabs}>
        <TabButton label="Briefings" active={tab === "briefings"} onPress={() => setTab("briefings")} />
        <TabButton label="Reminders" active={tab === "reminders"} onPress={() => setTab("reminders")} />
      </View>

      <View style={{ flex: 1, display: tab === "briefings" ? "flex" : "none" }}>
        <HomeScreen
          listenSignal={listenSignal}
          onReminderSaved={() => setReminderSignal((n) => n + 1)}
        />
      </View>
      <View style={{ flex: 1, display: tab === "reminders" ? "flex" : "none" }}>
        <RemindersScreen refreshSignal={reminderSignal} />
      </View>
    </SafeAreaView>
  );
}

function TabButton({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress} style={[styles.tab, active && styles.tabActive]}>
      <Text style={[styles.tabText, active && styles.tabTextActive]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.ink },
  header: {
    alignItems: "center",
    paddingTop: 18,
    paddingBottom: 10,
  },
  wordmark: {
    fontFamily: fonts.display,
    fontSize: 24,
    letterSpacing: 6,
    color: colors.brassBright,
  },
  tagline: {
    fontFamily: fonts.displayItalic,
    fontSize: 12,
    color: colors.parchmentFaint,
    marginTop: 2,
  },
  tabs: {
    flexDirection: "row",
    alignSelf: "center",
    backgroundColor: colors.inkRaised,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.hairline,
    padding: 4,
    marginTop: 8,
    marginBottom: 6,
    gap: 4,
  },
  tab: { borderRadius: 999, paddingHorizontal: 22, paddingVertical: 8 },
  tabActive: { backgroundColor: colors.brass },
  tabText: {
    fontFamily: fonts.bodySemi,
    fontSize: 13,
    letterSpacing: 0.4,
    color: colors.parchmentDim,
  },
  tabTextActive: { color: colors.ink },
});
