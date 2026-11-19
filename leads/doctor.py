"""'python -m leads doctor': tells you what is still missing before the agent can use real data. Changes nothing."""
import json
import os
import sys
from pathlib import Path

from . import drafts, store

ROOT = Path(__file__).parent.parent


def checks() -> list[tuple[bool, str]]:
    out = [(sys.version_info >= (3, 11), f"Python 3.11 or newer (this is {sys.version.split()[0]})")]
    has = drafts.SETTINGS.exists()
    out.append((has, "leads/settings.json exists (copy settings.example.json)"))
    if has:
        s = json.loads(drafts.SETTINGS.read_text(encoding="utf-8"))
        todo = [k for k, v in s.items() if "FILL IN" in json.dumps(v)]
        out.append((not todo, "Settings filled in" + (": still FILL IN -> " + ", ".join(todo) if todo else "")))
    for label, path in (("Invoices imported", store.DATA / "invoices.csv"),
                        ("Briefing inputs (calendar, emails)", ROOT / "boss" / "data" / "inputs.json"),
                        ("Bookings and loads imported", ROOT / "boss" / "data" / "team.json"),
                        ("Daily activity and goals imported", ROOT / "boss" / "data" / "activity.json")):
        out.append((path.exists(), f"{label} (real data, not sample)"))
    out.append((bool(os.environ.get("GEMINI_API_KEY")), "GEMINI_API_KEY set (lead finder, video lessons)"))
    out.append((bool(os.environ.get("OPENAI_API_KEY")), "OPENAI_API_KEY set (ChatGPT checker; optional until the card works)"))
    return out


def report() -> str:
    lines = [("[ok]   " if ok else "[todo] ") + msg for ok, msg in checks()]
    done = sum(ok for ok, _ in checks())
    return "\n".join(lines + ["", f"{done} of {len(lines)} ready. Nothing was changed."])
