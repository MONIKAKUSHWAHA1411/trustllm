# "Hey Siri, ask Sarathi"

Phase 1 uses an Apple Shortcut that deep-links into the app's listening state.
(A native App Intent can replace this in Phase 2; it needs a custom native module.)

The app registers the URL scheme `sarathi://` and treats `sarathi://listen` as
"open + start listening immediately" — the orb begins recording as soon as the
app is in the foreground.

## One-time setup (2 minutes, on the iPhone)

1. Install the Sarathi app first (dev client or TestFlight build).
2. Open the **Shortcuts** app → **+** to create a new shortcut.
3. Add the action **Open URLs** (search "URL" → "Open URLs").
4. Set the URL to: `sarathi://listen`
5. Tap the shortcut name at the top → rename it to **Ask Sarathi**.
   The name is the Siri phrase.
6. Done. Say **"Hey Siri, ask Sarathi"** — the app opens with the orb already
   listening.

Tips:

- Add the same shortcut to the Home Screen or Lock Screen widget for one-tap access.
- If Siri responds "you'll need to continue in the app", that's normal for
  URL-opening shortcuts — the app still opens and starts listening.
- If the phrase doesn't trigger, say "Run Ask Sarathi" once; Siri learns it quickly.
