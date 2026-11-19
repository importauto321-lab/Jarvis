"""Video-learning engine: give it a YouTube link, Gemini watches it and proposes key lessons.
Live-only (needs GEMINI_API_KEY and --live). Proposals are saved as PENDING; Dee approves or rejects."""
import json
import os
import re
import urllib.request

from . import library

MODEL = "gemini-2.5-flash"
URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"


def _ask(parts, key, post=None) -> str:
    body = json.dumps({"contents": [{"parts": parts}]}).encode()
    req = urllib.request.Request(URL.format(MODEL), body,
                                 {"Content-Type": "application/json", "x-goog-api-key": key})
    with (post or urllib.request.urlopen)(req, timeout=120) as r:
        data = json.load(r)
    return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])


def learn_video(url: str, key: str = "", post=None) -> dict:
    key = key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("Set GEMINI_API_KEY first (free key from aistudio.google.com).")
    if not re.match(r"https://(www\.)?(youtube\.com|youtu\.be)/", url):
        raise SystemExit("That is not a YouTube link.")
    prompt = ("Watch this video. Reply with ONLY a JSON object: title, lessons (3 to 6 short, specific, true "
              "takeaways from the video itself, no filler), tags (up to 5 words), route_to (one of: sales, loads, "
              "office, boss, life). Do not add anything the video did not say.")
    text = _ask([{"file_data": {"file_uri": url}}, {"text": prompt}], key, post)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise SystemExit("Gemini did not return lessons. Nothing was saved.")
    info = json.loads(m.group(0))
    return library.add("video", info.get("title") or url, url, info.get("lessons", []),
                       info.get("tags", []), info.get("route_to", "life"))
