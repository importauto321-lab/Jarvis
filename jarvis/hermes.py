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
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Optional, Tuple

DEFAULT_URL = "http://127.0.0.1:8642"
DEFAULT_ENV_FILE = Path.home() / ".hermes" / ".env"

INSTRUCTIONS = (
    "A voice assistant named Jarvis is passing you a task from its owner. Your reply will be read "
    "aloud, so finish with one to three short, plain spoken sentences: no markdown, bullet points, "
    "code, or links. The system pauses and asks the owner before anything that deletes, sends, pays, "
    "or changes something. If the owner says no or it is refused, do not try another way; say so. "
    "In the browser, start every step with a short comment saying what it does, naming any button or link "
    "you click; if it sends, pays, deletes, posts or signs in, use that word. Do not hide what a step does. "
    "Never invent facts; say what you could not do."
)


BROWSER_JOB_MARK = "Browse for this whole job"  # must match tools/hermes_gate.py


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


def ask(task: str, url: str = "", key: str = "", timeout: float = 300,
        approve: Optional[Callable[[str], bool]] = None, post: Optional[Callable] = None,
        sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic) -> str:
    """Send ``task`` to Hermes and return its answer.

    When Hermes wants to do something risky it waits; ``approve(description)`` must return True for it
    to go ahead, once. With no ``approve``, or on any doubt, the answer is no.
    """
    url = (url or os.environ.get("JARVIS_HERMES_URL", "") or DEFAULT_URL).rstrip("/")
    key = key or read_key()
    if not key:
        raise HermesError("I can't reach Hermes because its key isn't set up yet.")

    def call(path: str, body: Optional[dict] = None) -> dict:
        req = urllib.request.Request(url + path, None if body is None else json.dumps(body).encode(),
                                     {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        try:
            with (post or urllib.request.urlopen)(req, timeout=30) as r:
                data = json.load(r)
            if not isinstance(data, dict):
                raise ValueError("not an object")
            return data
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise HermesError("Hermes turned down my key. Check the key in the Hermes settings file.")
            raise HermesError(f"Hermes returned error {e.code}.")
        except urllib.error.URLError:
            raise HermesError("I can't reach Hermes. Open the Hermes app and try again.")
        except (TimeoutError, OSError):
            raise HermesError("Hermes stopped answering. It may still be working on it.")
        except (ValueError, TypeError):
            raise HermesError("Hermes answered in a form I didn't expect.")

    run_id = call("/v1/runs", {"input": task, "instructions": INSTRUCTIONS}).get("run_id")
    if not run_id:
        raise HermesError("Hermes answered in a form I didn't expect.")
    run_path = "/v1/runs/" + urllib.parse.quote(str(run_id), safe="")
    answered: set = set()
    deadline = clock() + timeout
    while clock() < deadline:
        state = call(run_path)
        status = state.get("status")
        if status == "completed":
            return str(state.get("output") or "").strip() or "Hermes finished but had nothing to say."
        if status in ("failed", "cancelled", "interrupted", "unknown"):
            raise HermesError("Hermes couldn't finish that task.")
        if status == "waiting_for_approval":
            for item in pending_approvals(state):
                prompt = item.get("prompt_id") or item.get("description") or ""
                if prompt in answered:
                    continue
                answered.add(prompt)
                asked_at = clock()
                asked = what_is_asked(item)
                yes = bool(approve and approve(asked))
                deadline += clock() - asked_at  # time spent deciding doesn't count
                whole_job = asked.startswith(BROWSER_JOB_MARK)  # one yes covers this job's ordinary browsing
                body = {"choice": ("session" if whole_job else "once") if yes else "deny"}
                if item.get("prompt_id"):
                    body.update(request_id=item["prompt_id"], execution_generation=item.get("execution_generation"))
                call(run_path + "/approval", body)
        sleep(1)
    try:
        call(run_path + "/stop", {})
    except HermesError:
        pass
    raise HermesError("Hermes took too long, so I told it to stop.")


def what_is_asked(item: dict) -> str:
    """The reason plus the actual command, so a yes is never given without seeing it."""
    reason, command = str(item.get("description") or ""), str(item.get("command") or "")
    if command and not command.startswith("<") and command not in reason:
        reason = f"{reason}: {command}" if reason else command
    return reason or "something it did not describe"


def pending_approvals(state: dict) -> list:
    """The permission requests in a run's status."""
    items = state.get("pending_controls") or ([state["approval"]] if state.get("approval") else [])
    return [i for i in items if isinstance(i, dict) and i.get("kind", "approval") == "approval"]


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
