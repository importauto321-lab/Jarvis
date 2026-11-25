"""Send a task to a Hermes Agent running on this computer and get the answer back.

Hermes's local API server must be on (``API_SERVER_ENABLED=true`` and
``API_SERVER_KEY=...`` in ``~/.hermes/.env``). It only listens on this computer
and always needs the key. Jarvis reads the key from ``JARVIS_HERMES_KEY`` or,
if that is not set, from the ``API_SERVER_KEY`` line in the Hermes env file.
The key is never printed or logged.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional, Tuple

DEFAULT_URL = "http://127.0.0.1:8642"
DEFAULT_ENV_FILE = Path.home() / ".hermes" / ".env"

INSTRUCTIONS = (
    "A voice assistant named Jarvis is passing you a task from its owner. Your reply will be read "
    "aloud, so finish with one to three short, plain spoken sentences: no markdown, bullet points, "
    "code, or links. Draft only: never send a message or email, spend or move money, post, book, "
    "or delete anything, and never change settings, without the owner's clear OK. If a step needs "
    "approval, say so briefly and stop. Never invent facts; say what you could not do."
)


class HermesError(Exception):
    """The task could not be sent or no answer came back. The message is safe to speak."""


def read_key(env_file: Optional[Path] = None) -> str:
    key = os.environ.get("JARVIS_HERMES_KEY", "").strip()
    if key:
        return key
    path = env_file or DEFAULT_ENV_FILE
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("API_SERVER_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    except OSError:
        pass
    return ""


def ask(task: str, url: str = "", key: str = "", timeout: float = 300, post: Optional[Callable] = None) -> str:
    """Send ``task`` to Hermes and return its full text answer."""
    url = (url or os.environ.get("JARVIS_HERMES_URL", "") or DEFAULT_URL).rstrip("/")
    key = key or read_key()
    if not key:
        raise HermesError("I can't reach Hermes because its key isn't set up yet.")
    body = json.dumps({
        "model": "hermes-agent",
        "messages": [{"role": "system", "content": INSTRUCTIONS}, {"role": "user", "content": task}],
        "stream": False,
    }).encode()
    req = urllib.request.Request(url + "/v1/chat/completions", body,
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    try:
        with (post or urllib.request.urlopen)(req, timeout=timeout) as r:
            data = json.load(r)
        choice = data["choices"][0]
        text = (choice["message"]["content"] or "").strip()
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise HermesError("Hermes turned down my key. Check the key in the Hermes settings file.")
        raise HermesError(f"Hermes returned error {e.code}.")
    except urllib.error.URLError:
        raise HermesError("I can't reach Hermes. Open the Hermes app and try again.")
    except (TimeoutError, OSError):
        raise HermesError("Hermes is taking too long. It may still be working on it.")
    except (KeyError, IndexError, ValueError, TypeError):
        raise HermesError("Hermes answered in a form I didn't expect.")
    if choice.get("finish_reason") in ("error", "cancelled"):
        raise HermesError("Hermes couldn't finish that task.")
    return text or "Hermes finished but had nothing to say."


_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_URL = re.compile(r"https?://\S+")
_MARKUP = re.compile(r"[*_`#>|~]+")
_BULLET = re.compile(r"^\s*(?:[-+•]|\d+[.)])\s+", re.MULTILINE)


def speakable(text: str, max_sentences: int = 3, max_chars: int = 400) -> Tuple[str, bool]:
    """Turn an answer into something pleasant to hear. Returns (spoken text, whether it was shortened)."""
    t = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    t = _LINK.sub(r"\1", t)
    t = _URL.sub("a link", t)
    t = _BULLET.sub("", t)
    t = _MARKUP.sub("", t)
    t = re.sub(r"\s*\n+\s*", ". ", t)
    t = re.sub(r"\.(\s*\.)+", ".", t)
    t = re.sub(r"\s+", " ", t).strip()
    sentences = re.split(r"(?<=[.!?])\s+", t)
    spoken = " ".join(sentences[:max_sentences])
    shortened = len(sentences) > max_sentences
    if len(spoken) > max_chars:
        spoken = spoken[:max_chars].rsplit(" ", 1)[0].rstrip(",;:") + "."
        shortened = True
    return spoken or "Done.", shortened
