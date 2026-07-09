import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Modal,
  Platform,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import DateTimePicker from "@react-native-community/datetimepicker";
import { deleteReminder, getReminders, updateReminder } from "../api";
import { removeCalendarEvent } from "../lib/calendar";
import { colors, fonts } from "../theme";
import type { Reminder } from "../types";

function formatDue(iso: string | null): string {
  if (!iso) return "No time set";
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

interface Props {
  /** Bumped by HomeScreen when a new reminder is created. */
  refreshSignal: number;
}

export function RemindersScreen({ refreshSignal }: Props) {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [editing, setEditing] = useState<Reminder | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDate, setEditDate] = useState<Date>(new Date());

  const load = useCallback(async () => {
    try {
      const rows = await getReminders();
      setReminders(rows);
    } catch {
      // keep whatever we have
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshSignal]);

  const openEditor = (r: Reminder) => {
    setEditing(r);
    setEditTitle(r.title);
    setEditDate(r.due_at ? new Date(r.due_at) : new Date());
  };

  const saveEdit = async () => {
    if (!editing) return;
    const patch = { title: editTitle.trim() || editing.title, due_at: editDate.toISOString() };
    setEditing(null);
    const updated = await updateReminder(editing.id, patch).catch(() => null);
    if (updated) {
      setReminders((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    }
  };

  const confirmDelete = (r: Reminder) => {
    Alert.alert("Delete reminder?", r.title, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          setReminders((prev) => prev.filter((x) => x.id !== r.id));
          if (r.calendar_event_id) await removeCalendarEvent(r.calendar_event_id);
          deleteReminder(r.id).catch(() => {});
        },
      },
    ]);
  };

  const markDone = async (r: Reminder) => {
    setReminders((prev) => prev.filter((x) => x.id !== r.id));
    updateReminder(r.id, { status: "done" }).catch(() => {});
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.brass} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1 }}>
      {reminders.length === 0 ? (
        <View style={styles.center}>
          <Text style={styles.emptyTitle}>Nothing pending.</Text>
          <Text style={styles.emptyBody}>
            Say “remind me…” from the briefing screen and it will appear here and in
            your calendar.
          </Text>
        </View>
      ) : (
        <FlatList
          data={reminders}
          keyExtractor={(r) => r.id}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                load();
              }}
              tintColor={colors.brass}
            />
          }
          contentContainerStyle={{ paddingVertical: 12, paddingBottom: 120 }}
          renderItem={({ item }) => (
            <View style={styles.row}>
              <Pressable style={styles.doneDot} onPress={() => markDone(item)}>
                <View style={styles.doneDotInner} />
              </Pressable>
              <Pressable style={{ flex: 1 }} onPress={() => openEditor(item)}>
                <Text style={styles.title}>{item.title}</Text>
                <Text style={styles.due}>{formatDue(item.due_at)}</Text>
                {item.notes ? (
                  <Text style={styles.notes} numberOfLines={2}>
                    {item.notes}
                  </Text>
                ) : null}
              </Pressable>
              <Pressable onPress={() => confirmDelete(item)} hitSlop={10}>
                <Text style={styles.delete}>✕</Text>
              </Pressable>
            </View>
          )}
        />
      )}

      <Modal visible={editing !== null} transparent animationType="slide">
        <View style={styles.modalScrim}>
          <View style={styles.modalCard}>
            <Text style={styles.modalHeading}>Edit reminder</Text>
            <TextInput
              value={editTitle}
              onChangeText={setEditTitle}
              style={styles.input}
              placeholder="Title"
              placeholderTextColor={colors.parchmentFaint}
            />
            <DateTimePicker
              value={editDate}
              mode="datetime"
              display={Platform.OS === "ios" ? "spinner" : "default"}
              themeVariant="dark"
              onChange={(_, d) => d && setEditDate(d)}
            />
            <View style={styles.modalActions}>
              <Pressable onPress={() => setEditing(null)}>
                <Text style={styles.modalCancel}>Cancel</Text>
              </Pressable>
              <Pressable onPress={saveEdit} style={styles.modalSaveBtn}>
                <Text style={styles.modalSave}>Save</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 36 },
  emptyTitle: {
    fontFamily: fonts.display,
    fontSize: 28,
    color: colors.parchment,
    marginBottom: 10,
  },
  emptyBody: {
    fontFamily: fonts.body,
    fontSize: 14,
    lineHeight: 22,
    color: colors.parchmentDim,
    textAlign: "center",
  },
  row: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 14,
    backgroundColor: colors.inkRaised,
    borderWidth: 1,
    borderColor: colors.hairline,
    borderRadius: 16,
    padding: 16,
    marginHorizontal: 16,
    marginBottom: 10,
  },
  doneDot: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 1.5,
    borderColor: colors.brass,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 2,
  },
  doneDotInner: { width: 10, height: 10, borderRadius: 5 },
  title: { fontFamily: fonts.bodySemi, fontSize: 16, color: colors.parchment },
  due: {
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
    color: colors.brassBright,
    marginTop: 3,
  },
  notes: {
    fontFamily: fonts.body,
    fontSize: 13,
    color: colors.parchmentDim,
    marginTop: 4,
  },
  delete: { color: colors.parchmentFaint, fontSize: 16, padding: 2 },
  modalScrim: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(4, 8, 15, 0.7)",
  },
  modalCard: {
    backgroundColor: colors.inkRaised2,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    paddingBottom: 44,
    borderWidth: 1,
    borderColor: colors.hairline,
  },
  modalHeading: {
    fontFamily: fonts.display,
    fontSize: 22,
    color: colors.parchment,
    marginBottom: 16,
  },
  input: {
    fontFamily: fonts.bodyMedium,
    fontSize: 16,
    color: colors.parchment,
    backgroundColor: colors.ink,
    borderWidth: 1,
    borderColor: colors.hairline,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 12,
  },
  modalActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
    gap: 24,
    marginTop: 12,
  },
  modalCancel: { fontFamily: fonts.bodyMedium, fontSize: 15, color: colors.parchmentDim },
  modalSaveBtn: {
    backgroundColor: colors.brass,
    borderRadius: 999,
    paddingHorizontal: 24,
    paddingVertical: 10,
  },
  modalSave: { fontFamily: fonts.bodySemi, fontSize: 15, color: colors.ink },
});
