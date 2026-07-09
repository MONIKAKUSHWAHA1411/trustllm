import cors from "cors";
import express, { NextFunction, Request, Response } from "express";
import { askSarathi } from "./claude";
import { supabase } from "./supabase";

const app = express();
app.use(cors());
app.use(express.json({ limit: "1mb" }));

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, service: "sarathi-backend" });
});

/**
 * POST /api/ask { transcript, timezone }
 * Classifies + answers via Claude (web search enabled), persists the briefing,
 * and creates a reminder row when Claude returns reminder JSON.
 */
app.post("/api/ask", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const transcript = String(req.body?.transcript ?? "").trim();
    const timezone = String(req.body?.timezone ?? "Asia/Kolkata");
    if (!transcript) {
      res.status(400).json({ error: "transcript is required" });
      return;
    }

    const answer = await askSarathi(transcript, timezone);
    const db = supabase();

    let reminderId: string | null = null;
    if (answer.reminder) {
      const { data, error } = await db
        .from("reminders")
        .insert({
          title: answer.reminder.title,
          notes: answer.reminder.notes,
          due_at: answer.reminder.due_at,
          location: answer.reminder.location,
          source_transcript: transcript,
        })
        .select()
        .single();
      if (error) throw new Error(`reminder insert failed: ${error.message}`);
      reminderId = data.id;
    }

    const { data: briefing, error: bErr } = await db
      .from("briefings")
      .insert({
        query: transcript,
        type: answer.type,
        spoken: answer.spoken,
        detail: answer.detail,
        sources: answer.sources,
        reminder_id: reminderId,
      })
      .select()
      .single();
    if (bErr) throw new Error(`briefing insert failed: ${bErr.message}`);

    res.json({
      ...answer,
      briefing_id: briefing.id,
      reminder_id: reminderId,
    });
  } catch (err) {
    next(err);
  }
});

/** GET /api/briefings?limit=50 — newest first, for reload on app open. */
app.get("/api/briefings", async (req, res, next) => {
  try {
    const limit = Math.min(Number(req.query.limit) || 50, 200);
    const { data, error } = await supabase()
      .from("briefings")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(limit);
    if (error) throw new Error(error.message);
    res.json(data);
  } catch (err) {
    next(err);
  }
});

/** GET /api/reminders — pending reminders, soonest first. */
app.get("/api/reminders", async (_req, res, next) => {
  try {
    const { data, error } = await supabase()
      .from("reminders")
      .select("*")
      .eq("status", "pending")
      .order("due_at", { ascending: true, nullsFirst: false })
      .limit(200);
    if (error) throw new Error(error.message);
    res.json(data);
  } catch (err) {
    next(err);
  }
});

/** PATCH /api/reminders/:id — edit title/notes/due_at/status/calendar_event_id. */
app.patch("/api/reminders/:id", async (req, res, next) => {
  try {
    const allowed = ["title", "notes", "due_at", "status", "calendar_event_id", "location"] as const;
    const patch: Record<string, unknown> = { updated_at: new Date().toISOString() };
    for (const key of allowed) {
      if (key in (req.body ?? {})) patch[key] = req.body[key];
    }
    const { data, error } = await supabase()
      .from("reminders")
      .update(patch)
      .eq("id", req.params.id)
      .select()
      .single();
    if (error) throw new Error(error.message);
    res.json(data);
  } catch (err) {
    next(err);
  }
});

/** DELETE /api/reminders/:id */
app.delete("/api/reminders/:id", async (req, res, next) => {
  try {
    const { error } = await supabase().from("reminders").delete().eq("id", req.params.id);
    if (error) throw new Error(error.message);
    res.json({ ok: true });
  } catch (err) {
    next(err);
  }
});

// eslint-disable-next-line @typescript-eslint/no-unused-vars
app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error("[sarathi]", err);
  res.status(500).json({ error: err.message || "Internal error" });
});

export default app;
