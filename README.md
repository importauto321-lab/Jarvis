# Jarvis — a Python voice assistant

Say the wake word, then a command:

> **"Jarvis, what time is it?"** → *"It's 2:05 PM."*
> **"Jarvis, set a timer for 5 minutes."**
> **"Jarvis, why is the sky blue?"** → answered by Claude

Built-in skills run locally and instantly. Anything they don't cover goes to
Claude (if you've set an API key), which replies in short sentences meant to be
spoken aloud and remembers the conversation.

## iPad and phone version (web)

`docs/index.html` is a standalone web version: tap the circle and talk, and
Jarvis answers out loud. It uses the browser's own speech recognition and
voice, so it works in Safari on iPad and iPhone and in Chrome on a computer.

Host it free with GitHub Pages: in the repo's **Settings → Pages**, set
**Source** to *Deploy from a branch*, pick `main` and the `/docs` folder, and
save. After a minute it's live at
`https://importauto321-lab.github.io/Jarvis/`.

Built-in commands work right away. For general questions, tap **Settings** and
paste an Anthropic API key; it's stored only in that browser.

Tap the circle once to start a conversation: after each answer Jarvis starts
listening again by itself, so there's nothing to press. Tap the circle (or say
"stop listening") to pause; it also pauses after a few quiet turns. Pick a
voice under **Settings → Voice**; the choice is saved in that browser.

### Texting

Ask Jarvis to text someone ("text Mom that I'm running late", or "text 555 123
4567 saying on my way"). It writes the message and shows it with an
**Open in Messages** button, which opens Messages with the text filled in; you
tap Send. It's free: the text goes through your own Messages app, and Jarvis
never sends anything itself. Saying "...saying <exact words>" works without an
API key. On an iPad, texts to non-Apple phones need Text Message Forwarding
from your iPhone (iPhone Settings → Apps → Messages → Text Message Forwarding).

### Calling

Say "call 555 123 4567" or "call Mom at 555 123 4567", and Jarvis shows the
number with a **Call** button; tap it to start the call. It's free: the call
goes through your own phone, and Jarvis never dials by itself. Jarvis can't see
your contacts, so it needs the number. With an API key and Gmail connected,
"call the person who emailed me about the invoice" works too, using a number
from that email. On an iPad, Call offers FaceTime Audio, or a normal phone call
through your iPhone if "Calls on Other Devices" is on (iPhone Settings → Apps →
Phone → Calls on Other Devices).

### Gmail and Calendar setup

The web version can check your calendar and search and read your email. It
asks Google for read-only access by default. To let it send email and add
calendar events too, turn on **Let Jarvis send email and add calendar events**
in Settings and connect again. Even then, nothing is sent or added until you
confirm the details it shows you. If the email address came from an email
rather than from you, you have to tap **Yes**; saying "yes" isn't enough.

It signs in to Google with your own OAuth client ID. Create one once, in
Safari or any browser:

1. Go to [console.cloud.google.com](https://console.cloud.google.com), sign in,
   and create a project (for example "Jarvis").
2. Open **APIs & Services → Library** and enable **Gmail API** and
   **Google Calendar API**.
3. Open **Google Auth Platform** (OAuth consent screen). Choose **External**,
   name the app "Jarvis", and enter your email where asked. Under
   **Audience**, add your own Gmail address as a **test user**.
4. Open **Clients → Create client**. Pick **Web application**. Under
   **Authorized JavaScript origins**, add `https://importauto321-lab.github.io`.
   Create it and copy the **Client ID** (it ends in
   `.apps.googleusercontent.com`).
5. In Jarvis, open **Settings**, paste the Client ID, tap **Save ID**, then
   **Connect Google**. Google warns that the app isn't verified, because it's
   your own private app: tap **Continue** and allow access.

Jarvis stays signed in to Google on that device until you tap **Disconnect
Google**: the sign-in and your Google address are saved in the browser. Google
makes each sign-in run out after about an hour, and a site without its own
server can't renew it silently, so Jarvis renews it the next time you tap the
circle or send something. Because you already allowed access, Google's window
just opens and closes. Nothing is sent
anywhere except Google and, for answering your questions, Anthropic's API. The
page's Content Security Policy blocks every other site, and Anthropic's SDK is
served from this repository (`docs/vendor/`) rather than a CDN.

### Security

- Your Anthropic key and Google client ID are stored only in your browser.
  **Settings → Clear all keys** removes them and disconnects Google.
- Email and calendar content is treated as untrusted: it's never shown as
  HTML, and Jarvis is told never to follow instructions found in it.
- Jarvis can't delete, forward, archive or change email, or change or delete
  calendar events.
- Never commit keys or credential files; `.gitignore` blocks the common ones.

## Built-in skills

| Say | Does |
| --- | --- |
| "what time is it" / "what's the date" | Time and date |
| "what is 12 times 12" / "calculate 10 divided by 4" | Arithmetic (safe, no `eval`) |
| "set a timer for 30 seconds" | Timer that speaks when it's done |
| "open youtube" / "open example.org" | Opens a website |
| "search for pasta recipes" | Google search in your browser |
| "take a note buy milk" / "read my notes" | Notes saved to `~/.jarvis_notes.txt` |
| "tell me a joke", "hello", "what can you do" | Small talk |
| "goodbye" | Ends the session |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # optional: enables general questions
python -m jarvis
```

PyAudio needs PortAudio: `brew install portaudio` (macOS) or
`sudo apt install portaudio19-dev python3-pyaudio` (Debian/Ubuntu). On Linux,
pyttsx3 also needs `espeak` (`sudo apt install espeak`).

Speech-to-text uses Google's free web recognizer via `SpeechRecognition`, so it
needs internet. Text-to-speech (pyttsx3) runs offline.

## Options

```bash
python -m jarvis --text            # type instead of talk (no microphone needed)
python -m jarvis --mute            # print replies instead of speaking
python -m jarvis --wake-word erica # answer to a different name
python -m jarvis --no-wake-word    # respond to everything you say
python -m jarvis --no-ai           # built-in skills only
```

Environment variables: `JARVIS_NAME`, `JARVIS_WAKE_WORD`,
`JARVIS_REQUIRE_WAKE_WORD`, `JARVIS_MODEL` (default `claude-opus-5-5`),
`JARVIS_EFFORT` (default `low` for fast spoken replies), `JARVIS_VOICE_RATE`,
`JARVIS_NOTES_FILE`.

If the microphone or speech engine isn't available, Jarvis falls back to text
in / printed replies automatically.

## Adding a skill

```python
# jarvis/skills.py
@skill("coin", r"\bflip a coin\b", "flip a coin")
def _coin(ctx, m):
    return random.choice(["Heads.", "Tails."])
```

The first skill whose regex matches wins. A handler can raise `NotMine` to
pass the command on to the next skill (or to Claude).

## Layout

- `jarvis/assistant.py` — wake word handling and the listen → respond loop
- `jarvis/skills.py` — built-in skills and the `@skill` registry
- `jarvis/brain.py` — Claude conversation fallback
- `jarvis/speech.py` — microphone / keyboard input, voice / console output
- `tests/` — `pytest`

## Tests

```bash
pip install pytest && python -m pytest
```
