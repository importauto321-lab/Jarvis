"""Find and research leads with Gemini (free plan first). RESEARCH ONLY: never emails anyone.

Runs only with --live and a GEMINI_API_KEY in the environment. Results land as
status "candidate" so you can look at them before anything is drafted.
"""
import json
import os
import re
import urllib.request

from . import store

MODEL = "gemini-2.5-flash"
URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
MAX_PER_RUN = 10  # keeps every run small and cheap


def _ask(prompt: str, key: str, post=None) -> str:
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "tools": [{"google_search": {}}]}).encode()
    req = urllib.request.Request(URL.format(MODEL), body,
                                 {"Content-Type": "application/json", "x-goog-api-key": key})
    with (post or urllib.request.urlopen)(req, timeout=60) as r:
        data = json.load(r)
    return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])


def _json(text: str):
    m = re.search(r"(\[.*\]|\{.*\})", text, re.S)
    return json.loads(m.group(1)) if m else None


def find_prompt(kind: str, area: str, n: int) -> str:
    return (f"Use web search. Find up to {n} real {kind}s in or near {area} that ship or transport cars "
            "for others. Only include businesses you actually found on the web. Do not invent any. "
            'Reply with ONLY a JSON list of objects with keys: name, city_state, website, email, phone, '
            'ships_cars ("yes", "maybe" or "no"), notes (one specific fact about them). '
            "Leave a value empty if you did not see it. Never guess an email address.")


def find(kind: str, area: str, n: int = MAX_PER_RUN, key: str = "", post=None) -> list[dict]:
    key = key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("Set GEMINI_API_KEY first (free key from aistudio.google.com).")
    items = _json(_ask(find_prompt(kind, area, min(n, MAX_PER_RUN)), key, post)) or []
    added = []
    for it in items[:MAX_PER_RUN]:
        if not it.get("name") or (it.get("ships_cars") or "").lower() == "no":
            continue
        row = {k: str(it.get(k) or "") for k in store.FIELDS if k not in ("id", "status", "score")}
        row["kind"], row["status"] = kind, "candidate"
        if row["email"] and "@" not in row["email"]:
            row["email"] = ""
        added.append(store.add(row))
    return added


def research(lead_id: str, key: str = "", post=None) -> dict:
    """Look one lead up again and fill in ships_cars, email, phone and a notes sentence."""
    key = key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("Set GEMINI_API_KEY first.")
    lead = next((r for r in store.load() if r["id"] == str(lead_id)), None)
    if not lead:
        raise KeyError(f"no lead {lead_id}")
    prompt = (f"Use web search. Research {lead['name']} ({lead['city_state']}, {lead['website']}). "
              "Do they ship or transport cars for others? Reply with ONLY a JSON object: "
              'ships_cars ("yes"/"maybe"/"no"), email, phone, notes (one specific, true sentence). '
              "Leave empty what you did not see. Never guess an email.")
    info = _json(_ask(prompt, key, post)) or {}
    changes = {k: info[k] for k in ("ships_cars", "email", "phone", "notes") if info.get(k)}
    if "@" not in changes.get("email", "@"):
        changes.pop("email")
    return store.update(lead_id, **changes)
