import type { BriefingType } from "./theme";

export interface Source {
  title: string;
  url: string;
}

export interface ReminderPayload {
  title: string;
  notes: string | null;
  due_at: string | null; // ISO 8601 with timezone
  location: string | null;
}

export interface AskResponse {
  type: BriefingType;
  spoken: string;
  detail: string;
  sources: Source[];
  reminder: ReminderPayload | null;
  briefing_id: string;
  reminder_id: string | null;
}

export interface Briefing {
  id: string;
  query: string;
  type: BriefingType;
  spoken: string;
  detail: string | null;
  sources: Source[];
  reminder_id: string | null;
  created_at: string;
}

export interface Reminder {
  id: string;
  title: string;
  notes: string | null;
  due_at: string | null;
  location: string | null;
  status: "pending" | "done" | "cancelled";
  calendar_event_id: string | null;
  created_at: string;
}
