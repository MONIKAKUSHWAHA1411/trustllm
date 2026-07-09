# SARATHI — सारथी

A voice-first AI chief of staff for an Indian politician, running on iPhone via TestFlight.

Tap the brass orb, speak, and Sarathi answers aloud — backed by Claude with live web
search — while a briefing card lands in your feed. Say *"remind me…"* and the reminder is
saved to Supabase **and** written into your native iOS Calendar.

## Architecture

```
iPhone (Expo custom dev client)
│  expo-speech-recognition  → native iOS speech-to-text (SFSpeechRecognizer)
│  expo-speech              → text-to-speech replies
│  expo-calendar            → writes reminders to the native Calendar
│
└──HTTPS──▶ Vercel serverless (Node + Express, backend/)
            │  POST /api/ask        → Claude (claude-sonnet-4-6 + web_search tool)
            │  GET  /api/briefings  → briefing history
            │  CRUD /api/reminders
            │
            └──▶ Supabase Postgres (reminders, briefings)
```

> Note: the spec called for `@react-native-voice/voice`; that package is officially
> deprecated by its maintainers in favor of `expo-speech-recognition`, which wraps the
> same native iOS speech APIs and is what this app uses. Everything still requires a
> custom dev client (not Expo Go).

## Repo layout

| Path | What it is |
|---|---|
| `app/` | Expo (SDK 57) React Native app, TypeScript |
| `backend/` | Express app deployed as a Vercel serverless function |
| `supabase/migrations/` | Postgres schema (reminders, briefings) |
| `docs/SIRI.md` | "Hey Siri, ask Sarathi" shortcut setup |

## Query classification

Every transcript is classified by Claude into one of four briefing types, each styled
differently in the feed:

- **REMINDER** — parsed into structured JSON, saved to Supabase, written to iOS Calendar
- **MEDIA_WATCH** — news/press/sentiment, with web search + tappable sources
- **SPEECH_PREP** — talking points, quotes, stats for speeches and interviews
- **GENERAL** — everything else

The backend returns `{ type, spoken, detail, sources[], reminder|null }`; the app speaks
`spoken` and renders the card.

## Backend setup

Environment variables (Vercel → Project → Settings → Environment Variables):

| Var | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API keys |
| `SUPABASE_URL` | Supabase → Project Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API (service_role — server only, never in the app) |

Deploy: `cd backend && npx vercel --prod` (or the Vercel MCP/git integration).
Then put the deployment URL into `app/app.json` → `expo.extra.apiUrl`.

## Running the app (custom dev client)

Expo Go won't work — native speech recognition needs a dev client.

```bash
cd app
npm install
npx eas build --profile development --platform ios   # once; installs like TestFlight
npx expo start --dev-client                          # then run JS locally
```

## EAS Build → TestFlight walkthrough

One-time prerequisites:

1. **Apple Developer Program** membership ($99/yr) on the Apple ID that will distribute the app.
2. `npm i -g eas-cli` and an Expo account (`eas login`).

Steps:

1. **Configure the project** (from `app/`):
   ```bash
   eas init                      # links the app to your Expo account (creates projectId)
   eas build:configure           # writes eas.json (already committed — it will detect it)
   ```
2. **Development build on your iPhone** (for day-to-day iteration):
   ```bash
   eas build --profile development --platform ios
   ```
   - EAS asks to log in to your Apple account and creates certificates/provisioning
     profiles automatically.
   - When it asks to register a device, say yes and open the link on the iPhone —
     this installs a provisioning profile so the dev build runs on that phone.
   - When the build finishes, open the build URL on the phone and tap Install.
   - Then `npx expo start --dev-client` on your Mac and scan the QR code.
3. **TestFlight build** (what the politician installs):
   ```bash
   eas build --profile production --platform ios
   eas submit --platform ios     # uploads the finished build to App Store Connect
   ```
   - First run of `eas submit` asks for your App Store Connect App ID; if the app
     doesn't exist yet it can create it (bundle ID `com.monikakushwaha.sarathi`).
   - In App Store Connect → TestFlight, wait for processing (~10 min), then add the
     user as an **internal tester** (their Apple ID email). They install via the
     TestFlight app.
4. **Ship JS-only updates without rebuilding** (optional):
   ```bash
   eas update --branch production
   ```

## Siri

See [docs/SIRI.md](docs/SIRI.md) — a one-time Shortcuts-app setup so that
**"Hey Siri, ask Sarathi"** opens the app straight into listening mode via the
`sarathi://listen` deep link.

## Phase 1 checklist

- [x] Tap-to-talk pulsing voice orb (native STT)
- [x] Claude backend with web search + query classification
- [x] TTS replies + typed briefing cards with tappable sources
- [x] Reminders → Supabase + native iOS Calendar
- [x] Reminders tab (edit / complete / delete)
- [x] Briefing history persisted and reloaded on open
- [x] Siri deep link into listening state
