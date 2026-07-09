import Constants from "expo-constants";
import type { AskResponse, Briefing, Reminder } from "./types";

const API_URL: string =
  process.env.EXPO_PUBLIC_API_URL ??
  (Constants.expoConfig?.extra?.apiUrl as string) ??
  "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_URL || API_URL.includes("REPLACE-AFTER-DEPLOY")) {
    throw new Error(
      "Backend URL not configured. Set EXPO_PUBLIC_API_URL or expo.extra.apiUrl in app.json."
    );
  }
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body.slice(0, 300)}`);
  }
  return (await res.json()) as T;
}

export function ask(transcript: string): Promise<AskResponse> {
  return request<AskResponse>("/api/ask", {
    method: "POST",
    body: JSON.stringify({
      transcript,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone ?? "Asia/Kolkata",
    }),
  });
}

export function getBriefings(): Promise<Briefing[]> {
  return request<Briefing[]>("/api/briefings?limit=50");
}

export function getReminders(): Promise<Reminder[]> {
  return request<Reminder[]>("/api/reminders");
}

export function updateReminder(
  id: string,
  patch: Partial<Pick<Reminder, "title" | "notes" | "due_at" | "status" | "calendar_event_id">>
): Promise<Reminder> {
  return request<Reminder>(`/api/reminders/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deleteReminder(id: string): Promise<{ ok: true }> {
  return request<{ ok: true }>(`/api/reminders/${id}`, { method: "DELETE" });
}
