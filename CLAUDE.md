# Jarvis — project memory

Read this first in every new session. It sums up earlier sessions so the user doesn't have to repeat themselves.

## The user

- Calls the assistant (Claude, in these chats) **Erica**. Answer to that name.
- Runs a car import business (Import Auto; uses a TMS for loads; has looked at Retell AI for voice calls).
- Uses Jarvis mostly on an **iPad in Safari**. Not a programmer: give plain, numbered steps, not code talk.
- **Wants to save money.** Gemini stays on the free plan. Suggest costs only with a rough number, and prefer free options.
- Wants to conserve their Claude usage: keep replies short, batch work, and don't ask avoidable questions.
- Their Claude app can't show the secure credential form (it only offers Deny). Don't send it; if a key is needed,
  point them to the environment's settings in a web browser (claude.ai/code → environment **Jarvis** → Edit → Network secrets).

## What Jarvis is

- **Web Jarvis** (`docs/`, served by GitHub Pages at importauto321-lab.github.io/Jarvis). The main product.
  - `docs/app.js` is the whole app; `docs/index.html` holds the page, CSP and Settings; `docs/privacy.html` the privacy policy.
  - Claude (`claude-opus-5-5`, effort low, server-side fallbacks) answers anything the built-in skills don't.
    The system prompt changes mid-conversation (memory, tools), so requests set thinking `block_binding` to `drop_block`
    (beta `thinking-binding-controls-2026-08-01`); without it a replayed thinking block is a 400.
  - Client tools (in `GOOGLE_TOOLS`, which also holds non-Google tools): Gmail and Calendar (after Connect Google),
    `write_text_message`, `start_phone_call`, `get_weather` (Open-Meteo, no key), `get_my_location` / `find_nearby`
    (only with Settings → Use my location; BigDataCloud names the city; Apple Maps link; with location on, every 3 h the
    next question carries a note asking for a weather heads-up with a what-to-wear tip, which the user asked for), `watch_youtube_video` (Gemini), `save_memory` / `update_memory` / `delete_memory`.
  - Server tool: Anthropic web search (`web_search_20260209`), limited to youtube.com, max 3 uses; only offered with a Gemini key.
    The tool loop resumes `pause_turn`.
  - **Memory** lives in localStorage (`jarvis.memory`) and is appended to the system prompt; Settings → Memory lists it.
  - **Hearing:** with a Gemini key, the circle records (MediaRecorder + loudness meter; stops after 2.5 s of quiet), converts to 16 kHz WAV, and Gemini
    transcribes (`HEARING_MODELS`, lite model first, thinking off, 15 s per model, one retry). If Gemini fails, Safari's own
    SpeechRecognition is used for 10 minutes. Without a key, Safari's SpeechRecognition (a fresh recognizer per tap).
  - **Gemini calls** go through `geminiGenerate()`: it first asks Google which Flash models the key can use (`geminiModelNames`,
    once per visit; the fixed lists are only a backup), retries busy models, then falls back across them; errors are
    `GeminiError` with a `kind` and a `detail` saying what each model returned.
- **Computer Jarvis** (`jarvis/`, Python, `python -m jarvis`). Same idea, simpler: skills, Claude with a tool loop,
  YouTube via `GEMINI_API_KEY`. Tests: `python -m pytest`.

## iPad Safari lessons (don't undo these)

- Start the microphone inside the tap. Never reuse a SpeechRecognition object; use timers so the circle can't stay red.
- Speech only plays if the page spoke during a tap: every tap says a silent word first (`unlockSpeech`).
- Opening the mic with echo cancellation, or leaving an AudioContext open, keeps the iPad in quiet "phone call" mode.
  Record with echoCancellation off, close the AudioContext after each recording, decode with OfflineAudioContext,
  and set `navigator.audioSession.type` to "playback" before speaking.
- Safari caches hard: scripts are linked with `?v=N`. **Bump "Page version N" and every `?v=N` in `docs/index.html` on each web change**,
  so the user can confirm they have the new version.

## How we work

- One branch per change, from the latest `origin/main`; open a PR and merge it (the user has asked for changes to go live).
- Test web changes in headless Chromium with Playwright before pushing: fake Claude/Gemini with `page.route`, a fake mic with
  `--use-fake-device-for-media-stream --use-file-for-fake-audio-capture=<wav>`, and fake `speechSynthesis` / SpeechRecognition.
  Say plainly that real iPad behavior can't be tested here.
- Update `docs/privacy.html` and `README.md` whenever what Jarvis stores or sends changes.
- The cloud environment **Jarvis** exists for this repo; it has no keys saved.

## Plans the user liked (not built yet)

The full plan the user agreed on is in `PLAN.md`. Show it to them when they ask about "the big plan".

1. Morning briefing: email, calendar and urgent items, every day (likely needs Anthropic Managed Agents scheduled deployments).
2. Move Jarvis's brain to Managed Agents, so it works when the iPad is off; the iPad page becomes the voice and screen.
3. Business tools: loads in the TMS, customer follow-ups, invoices.
4. Prompt caching to cut Claude costs (rough heavy-use estimate was $300–500/month without it; normal use $40–100).

The user wants to test that Jarvis talks and hears reliably before building more, then review these plans together.
