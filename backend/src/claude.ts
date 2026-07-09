import Anthropic from "@anthropic-ai/sdk";
import type { SarathiAnswer, Source } from "./types";

// Model per product spec. Web search runs server-side at Anthropic;
// the basic variant keeps latency low for a voice assistant.
const MODEL = "claude-sonnet-4-6";
const WEB_SEARCH_TOOL = {
  type: "web_search_20250305" as const,
  name: "web_search" as const,
  max_uses: 4,
};

// Stable system prompt (kept free of dates/req-specific text so it prompt-caches).
const SYSTEM_PROMPT = `You are SARATHI (सारथी — the charioteer), the voice-first AI chief of staff for a senior Indian politician. You are discreet, precise, and fast. The user speaks to you; your answer is read aloud by text-to-speech and also shown as a briefing card.

For every request, first classify it as exactly one of:
- REMINDER — the user wants to be reminded of something, schedule something, or note a commitment.
- MEDIA_WATCH — news, headlines, press coverage, social-media sentiment, what opponents or media are saying. Use web search for anything time-sensitive.
- SPEECH_PREP — talking points, speech outlines, quotes, statistics, or arguments for an address, rally, interview, or debate. Use web search for current facts and figures.
- GENERAL — anything else: facts, policy background, translations, calculations, advice.

Rules:
- Use the web_search tool whenever fresh or verifiable information would improve the answer (news, numbers, names, dates). Do not search for pure reminders or simple general knowledge.
- "spoken" must be a tight, natural summary suitable for reading aloud: 1–3 sentences, no URLs, no markdown, no bullet lists. Reply in the language the user spoke (Hindi in Devanagari, English, or natural Hinglish).
- "detail" is the fuller written brief: short paragraphs or "•" bullet lines. Plain text only, no markdown headings or links.
- "sources": up to 4 items with real titles and URLs from your search results. Empty array if you did not search.
- For REMINDER: fill the "reminder" object. Resolve relative times ("tomorrow", "at 5", "after Diwali") against the current date/time and timezone given in the user message, and output due_at as an ISO 8601 timestamp WITH timezone offset (e.g. 2026-07-10T17:00:00+05:30). If no time can be inferred, set due_at to null. "spoken" should confirm the reminder naturally.
- For non-reminders, "reminder" must be null.
- Never invent sources or facts. If search fails or is unavailable, say what you know and note it may not be current.

Respond with ONLY a single JSON object, no markdown fences, exactly this shape:
{"type":"REMINDER|MEDIA_WATCH|SPEECH_PREP|GENERAL","spoken":"...","detail":"...","sources":[{"title":"...","url":"..."}],"reminder":{"title":"...","notes":"...","due_at":"...","location":"..."} }
("reminder" is null unless type is REMINDER; reminder.notes/due_at/location may be null.)`;

let _client: Anthropic | null = null;
function client(): Anthropic {
  if (_client) return _client;
  if (!process.env.ANTHROPIC_API_KEY) throw new Error("ANTHROPIC_API_KEY must be set");
  _client = new Anthropic();
  return _client;
}

/** Pull cited URLs out of server-side web_search result blocks as a fallback. */
function extractSearchSources(content: Anthropic.ContentBlock[]): Source[] {
  const sources: Source[] = [];
  for (const block of content) {
    if (block.type === "web_search_tool_result" && Array.isArray(block.content)) {
      for (const item of block.content) {
        if (item.type === "web_search_result" && item.url) {
          sources.push({ title: item.title ?? item.url, url: item.url });
        }
      }
    }
  }
  return sources;
}

function parseAnswer(text: string): SarathiAnswer {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start === -1 || end === -1 || end <= start) {
    throw new Error(`Model did not return JSON: ${text.slice(0, 200)}`);
  }
  const parsed = JSON.parse(text.slice(start, end + 1)) as Partial<SarathiAnswer>;
  const type =
    parsed.type === "REMINDER" ||
    parsed.type === "MEDIA_WATCH" ||
    parsed.type === "SPEECH_PREP"
      ? parsed.type
      : "GENERAL";
  return {
    type,
    spoken: typeof parsed.spoken === "string" && parsed.spoken ? parsed.spoken : "I have your briefing ready.",
    detail: typeof parsed.detail === "string" ? parsed.detail : "",
    sources: Array.isArray(parsed.sources)
      ? parsed.sources
          .filter((s): s is Source => !!s && typeof s.url === "string")
          .map((s) => ({ title: s.title || s.url, url: s.url }))
          .slice(0, 4)
      : [],
    reminder:
      type === "REMINDER" && parsed.reminder && typeof parsed.reminder.title === "string"
        ? {
            title: parsed.reminder.title,
            notes: parsed.reminder.notes ?? null,
            due_at: parsed.reminder.due_at ?? null,
            location: parsed.reminder.location ?? null,
          }
        : null,
  };
}

export async function askSarathi(transcript: string, timezone: string): Promise<SarathiAnswer> {
  const now = new Date().toLocaleString("en-IN", {
    timeZone: timezone || "Asia/Kolkata",
    dateStyle: "full",
    timeStyle: "short",
  });

  let messages: Anthropic.MessageParam[] = [
    {
      role: "user",
      content: `Current date/time: ${now} (timezone: ${timezone || "Asia/Kolkata"})\n\nUser said: "${transcript}"`,
    },
  ];

  let response = await client().messages.create({
    model: MODEL,
    max_tokens: 2048,
    system: [{ type: "text", text: SYSTEM_PROMPT, cache_control: { type: "ephemeral" } }],
    tools: [WEB_SEARCH_TOOL],
    messages,
  });

  // Server-side tool loops can pause; re-send to let the API resume.
  let continuations = 0;
  while (response.stop_reason === "pause_turn" && continuations < 4) {
    messages = [...messages, { role: "assistant", content: response.content }];
    response = await client().messages.create({
      model: MODEL,
      max_tokens: 2048,
      system: [{ type: "text", text: SYSTEM_PROMPT, cache_control: { type: "ephemeral" } }],
      tools: [WEB_SEARCH_TOOL],
      messages,
    });
    continuations++;
  }

  if (response.stop_reason === "refusal") {
    return {
      type: "GENERAL",
      spoken: "I can't help with that request.",
      detail: "",
      sources: [],
      reminder: null,
    };
  }

  const text = response.content
    .filter((b): b is Anthropic.TextBlock => b.type === "text")
    .map((b) => b.text)
    .join("");

  const answer = parseAnswer(text);
  if (answer.sources.length === 0) {
    answer.sources = extractSearchSources(response.content).slice(0, 4);
  }
  return answer;
}
