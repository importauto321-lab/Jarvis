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
