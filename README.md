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

### Memory

Jarvis remembers things between conversations: what you tell him about
yourself, your preferences, and what he learned (for example the steps from a
video). Claude decides what's worth saving and says so in the chat, and you can
also say "remember that..." or "forget that...". Memories are stored only in
that browser and sent to Claude with each question. **Settings → Memory** lists
them, with **Forget** buttons and **Forget everything**.

### YouTube videos

To have Jarvis watch a YouTube video, get a free Gemini API key at
[aistudio.google.com/apikey](https://aistudio.google.com/apikey) and paste it
under **Settings → YouTube videos**. Then paste a video link and ask, for
example "summarize this https://youtu.be/..." or "what recipe do they make in
this video?". Claude passes the link to Gemini, which watches the picture and
sound, and Claude answers from that. The video must be public; very long videos
may hit Gemini's limits. You still need the Anthropic key too.

Jarvis can also find videos by itself: ask "find a video on changing brake
pads and teach me" or "watch the newest MrBeast video". Claude searches YouTube
with Anthropic's web search (limited to youtube.com, at most 3 searches per
question, about 1 cent each), picks a video, watches it through Gemini and
answers. It says which video it chose, and an **Open the video** link appears
under the answer.

With a Gemini key saved, the circle also uses Gemini to hear you: it records
until you stop talking, and Gemini writes down what you said. On iPad this is
much more reliable than Safari's own speech recognition, which often stops
hearing after the first question. Turn off **Use Gemini to hear me** in
Settings to go back to Safari's listening; then your voice isn't sent to Google.

With a Gemini key, Jarvis speaks with Gemini's natural voice instead of the
iPad's robotic one (free; pick the voice in **Settings → Voice engine**).
His answers are sent to Google to be spoken. If Gemini is busy or its free limit
runs out, the iPad voice takes over; choose **iPad voice** to keep answers on
the device.

Turn on **Use my location** in Settings to let Jarvis answer "what's the weather
here?", "find a gas station near me" (a button opens Apple Maps) or "how far am I
from...". Your location is checked only when a question needs it and sent to
Claude with that question; the weather comes from Open-Meteo and the city name
from BigDataCloud, both free with no key. Weather for a named city works even
with location off.

If Jarvis cuts you off, pick a longer wait under **Settings -> How long to wait after you
stop talking**. Tap the circle once to start a conversation: after each answer Jarvis starts
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
anywhere except Google (including Gemini, for YouTube videos), Anthropic's API for answering your questions, and, for location and weather, Open-Meteo and BigDataCloud. The
page's Content Security Policy blocks every other site, and Anthropic's SDK is
served from this repository (`docs/vendor/`) rather than a CDN.

### Security

- Your Anthropic key, Gemini key and Google client ID are stored only in your browser.
  **Settings → Clear all keys** removes them and disconnects Google.
- Email, calendar and video content is treated as untrusted: it's never shown as
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
| "ask Hermes to check my inbox" | Sends the task to Hermes and speaks the answer (see below) |
| "goodbye" | Ends the session |

## Talking to Hermes (Python version, on the computer that runs Hermes)

"Jarvis, ask Hermes to ..." (also "tell Hermes ...", "have Hermes ...") sends the task to
your local Hermes Agent and speaks its answer. Jarvis says "Sending that to Hermes", Hermes
does the work, and Jarvis reads back one to three short sentences. If the answer is longer,
the full text is printed on screen.

**Ask me first.** A Hermes hook (`tools/hermes_gate.py`) lets Hermes look at things on its own
but makes it wait for your yes before anything else: deleting, sending, paying, other
commands, writing files, code, browser actions and scheduled jobs. On the computer say "yes";
on the iPad tap **Yes**. Anything else is no. Install it by copying the script to
`~/.hermes/agent-hooks/ask_first.py`, adding it in `~/.hermes/config.yaml` as a
`pre_tool_call` hook with `fail_closed: true`, setting `approvals.mode: manual`, and
approving the hook. It is a safety net, not a sandbox: it can't stop every trick.

One-time setup: in `~/.hermes/.env` set `API_SERVER_ENABLED=true` and
`API_SERVER_KEY=<a long random secret>`, then restart Hermes. The server only listens on
this computer (`127.0.0.1:8642`). Jarvis reads the key from that file, or from
`JARVIS_HERMES_KEY`. Never commit the key. Other settings: `JARVIS_HERMES_URL`,
`JARVIS_HERMES_TIMEOUT` (seconds, default 300). Replies are spoken with `pyttsx3`, or the
Mac's built-in `say` voice if `pyttsx3` isn't installed.

### ChatGPT jobs (web page)

Add an OpenAI key under **Settings -> ChatGPT** for second opinions (including decisions about
real money), double-checking, code, writing, math, new or edited pictures, and voice
recordings. Jarvis says when he used it. Each use costs OpenAI credit. Whether something counts
as a money decision is Claude's judgment, so say "check it with ChatGPT" when it matters.

### Gemini jobs (web page)

With a Gemini key, current information (rates, news, prices) goes to Gemini with Google
Search, and **Attach** lets you send a picture, PDF, text file or audio recording (up to about 14 MB) for
Gemini to read or transcribe, and long email threads can be sent to Gemini too. Each
answer says when Gemini was used. Google's free limits apply, and free-tier data may be used
by Google, so keep sensitive documents out.

### From the iPad

On the web page you can just talk: with Hermes set up, Claude hands computer jobs to Hermes on
its own. If outside content (email, calendar, video, web) is in the conversation, it asks first.
The computer version still needs "ask Hermes".

The web page can reach Hermes over your own private Tailscale network. Install Tailscale on the
computer and the iPad with the same account, run `tailscale serve --bg 8642` on the computer
(keep Funnel off), and add `API_SERVER_CORS_ORIGINS=https://importauto321-lab.github.io` to
`~/.hermes/.env`. Then enter the address and key under **Settings -> Hermes** on the iPad. The
page's security policy only allows the `taila998e7.ts.net` network; change it in
`docs/index.html` for a different one.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # optional: enables general questions
export GEMINI_API_KEY=...             # optional: lets Jarvis watch YouTube videos
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
`JARVIS_NOTES_FILE`, `GEMINI_API_KEY`, `JARVIS_GEMINI_MODEL`.

### YouTube videos on the computer

With both keys set, type or paste a YouTube link with your question, for
example `summarize this https://youtu.be/...` (use `--text` so you can paste).
Claude passes the link to Gemini, which watches the video, and answers from
that. Get a free Gemini key at
[aistudio.google.com/apikey](https://aistudio.google.com/apikey). The video
must be public. If Gemini is busy, Jarvis retries, then moves on to the next free
Flash model. `JARVIS_GEMINI_MODEL` sets the models to try, comma-separated
(default `gemini-2.5-flash,gemini-flash-latest,gemini-flash-lite-latest`).

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
- `jarvis/hermes.py` — sends tasks to a local Hermes Agent
- `jarvis/youtube.py` — watching YouTube videos with Gemini, as a tool for Claude
- `jarvis/speech.py` — microphone / keyboard input, voice / console output
- `tests/` — `pytest`

## Tests

```bash
pip install pytest && python -m pytest
```
