export type BriefingType = "REMINDER" | "MEDIA_WATCH" | "SPEECH_PREP" | "GENERAL";

export interface Source {
  title: string;
  url: string;
}

export interface ReminderPayload {
  title: string;
  notes: string | null;
  due_at: string | null;
  location: string | null;
}

/** The structured object Claude must return (as JSON text). */
export interface SarathiAnswer {
  type: BriefingType;
  spoken: string;
  detail: string;
  sources: Source[];
  reminder: ReminderPayload | null;
}
