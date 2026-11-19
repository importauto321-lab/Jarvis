"""Delivery drafts: email to Nicole and Kaysha, email to the owner, a short text. NOTHING IS SENT HERE.
Each function writes a file you can read, then send yourself (or approve in Jarvis). Texting stays OFF until set up."""
import json
from datetime import date
from pathlib import Path

from leads import drafts

from . import briefing

OUT = Path(__file__).parent / "data" / "outbox"
TEXT_LIMIT = 450


def _write(name: str, body: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    p.write_text(body, encoding="utf-8")
    return p


def email_draft(kind: str, subject: str, text: str, today: date | None = None) -> Path:
    """kind: 'team' (to Nicole and Kaysha) or 'owner' (to the owner). Writes a draft file only."""
    today = today or date.today()
    key = "team_emails" if kind == "team" else "owner_email"
    s = drafts.load_settings([key])
    to = ", ".join(s[key]) if kind == "team" else s[key]
    return _write(f"{today.isoformat()}_{kind}_email.txt", f"To: {to}\nSubject: {subject}\n\n{text}\n\nDRAFT. NOT SENT.\n")


def short_text(inputs: dict, today: date | None = None) -> str:
    g = briefing.gather(inputs, today)
    parts = [f"Briefing {g['today']:%a %b %d}:"]
    if g["calendar"]:
        parts.append(f"{len(g['calendar'])} on calendar, first {g['calendar'][0]['time']} {g['calendar'][0]['title']}.")
    if g["emails"]:
        parts.append(f"{len(g['emails'])} email(s) need you: {g['emails'][0]['subject'][:50]}.")
    if g["drafts"]:
        parts.append("Drafts to OK: " + ", ".join(f"{v} {k}" for k, v in g["drafts"].items()) + ".")
    parts.append("Watch: " + g["watch"])
    t = " ".join(parts)
    return t if len(t) <= TEXT_LIMIT else t[:TEXT_LIMIT - 3] + "..."


def text_draft(text: str, today: date | None = None) -> Path:
    today = today or date.today()
    s = drafts.load_settings(["owner_text_number"])
    return _write(f"{today.isoformat()}_text.txt", f"To: {s['owner_text_number']}\n\n{text}\n\nDRAFT. NOT SENT.\n")


def send_text(*a, **k):
    """Texting is OFF until a texting service is set up and the owner turns it on. No sending code exists."""
    allowed = False
    if drafts.SETTINGS.exists():
        allowed = json.loads(drafts.SETTINGS.read_text(encoding="utf-8")).get("texting_allowed") is True
    raise SystemExit("Texting is off. Set it up at home first." if not allowed else "No texting service is connected yet.")
