import * as Calendar from "expo-calendar";
import { Platform } from "react-native";
import type { ReminderPayload } from "../types";

const SARATHI_CALENDAR_TITLE = "Sarathi";

async function getOrCreateCalendarId(): Promise<string> {
  const calendars = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);

  const existing = calendars.find((c) => c.title === SARATHI_CALENDAR_TITLE);
  if (existing) return existing.id;

  if (Platform.OS === "ios") {
    const writable = calendars.find((c) => c.allowsModifications);
    const source =
      calendars.find((c) => c.source?.name === "iCloud")?.source ??
      writable?.source;
    if (source) {
      try {
        return await Calendar.createCalendarAsync({
          title: SARATHI_CALENDAR_TITLE,
          color: "#C9A84C",
          entityType: Calendar.EntityTypes.EVENT,
          sourceId: source.id,
          name: SARATHI_CALENDAR_TITLE,
          ownerAccount: "personal",
          accessLevel: Calendar.CalendarAccessLevel.OWNER,
        });
      } catch {
        // fall through to default calendar
      }
    }
    const def = await Calendar.getDefaultCalendarAsync();
    return def.id;
  }

  const writable = calendars.find((c) => c.allowsModifications);
  if (!writable) throw new Error("No writable calendar found");
  return writable.id;
}

/**
 * Writes a reminder into the native calendar.
 * Returns the created event id, or null if permission was denied or no due date.
 */
export async function writeReminderToCalendar(
  reminder: ReminderPayload
): Promise<string | null> {
  if (!reminder.due_at) return null;

  const { granted } = await Calendar.requestCalendarPermissionsAsync();
  if (!granted) return null;

  const calendarId = await getOrCreateCalendarId();
  const start = new Date(reminder.due_at);
  const end = new Date(start.getTime() + 30 * 60 * 1000);

  return Calendar.createEventAsync(calendarId, {
    title: reminder.title,
    notes: reminder.notes ?? undefined,
    location: reminder.location ?? undefined,
    startDate: start,
    endDate: end,
    alarms: [{ relativeOffset: -30 }, { relativeOffset: 0 }],
  });
}

export async function removeCalendarEvent(eventId: string): Promise<void> {
  try {
    await Calendar.deleteEventAsync(eventId);
  } catch {
    // event may already be gone — not fatal
  }
}
