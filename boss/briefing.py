"""CEO morning briefing: short, same format every day (aim 250-500 words). Rules-based, $0 to build.

Inputs come from a JSON file (calendar, emails, ideas, watch, revenue_yesterday). Until real Gmail,
Calendar and Trucking Office access is plugged in at the house, boss/sample/inputs.json is used and the
briefing is stamped SAMPLE DATA. The draft counts come from the business agent's own folders.
"""
import json
from datetime import date
from pathlib import Path

from leads import inbox, invoices, store

HERE = Path(__file__).parent
MAX_WORDS = 500


def load_inputs(path: str | None = None) -> dict:
    p = Path(path) if path else HERE / "sample" / "inputs.json"
    return json.loads(p.read_text(encoding="utf-8"))


def drafts_waiting() -> dict:
    """How many drafts are waiting for the owner's OK (counted from files; nothing is sent)."""
    def n(d):
        p = Path(d)
        return len(list(p.glob("*.txt"))) if p.exists() else 0
    base = store.DATA
    return {"lead emails": n(base / "drafts"), "invoice reminders": n(base / "invoice_drafts" / "chase"),
            "demand letters (attorney must approve)": n(base / "invoice_drafts" / "demand"),
            "review requests": n(base / "invoice_drafts" / "review")}


def pick(items: list, today: date) -> str:
    return items[today.toordinal() % len(items)] if items else "Nothing today."


def gather(inputs: dict, today: date | None = None) -> dict:
    """The briefing's information as data. The text briefing and the dashboard both use this."""
    today = today or date.today()
    ranked = inbox.sort_messages(inputs.get("emails", []), today=today)
    return {
        "today": today, "sample": bool(inputs.get("sample")),
        "calendar": inputs.get("calendar", [])[:8],
        "emails": [m for m in ranked if m["tier"] in ("URGENT", "TODAY")][:5],
        "drafts": {k: v for k, v in drafts_waiting().items() if v},
        "late": invoices.unpaid_report(today)[:3],
        "idea": pick(inputs.get("ideas", []), today),
        "watch": pick(inputs.get("watch", []), today),
        "revenue": inputs.get("revenue_yesterday"),
    }


REV_MISSING = "Not connected yet. Needs read-only Trucking Office access, set up at the house."


def build(inputs: dict, today: date | None = None) -> str:
    g = gather(inputs, today)
    out = [f"CEO BRIEFING, {g['today']:%A %B %d}" + ("  [SAMPLE DATA, not real]" if g["sample"] else "")]
    out += ["", "1. Today's calendar and deadlines"]
    out += [f"   {e['time']}  {e['title']}" for e in g["calendar"]] or ["   Nothing scheduled."]
    out += ["", "2. Emails that need you personally"]
    out += [f"   [{m['tier']}] {m['subject'][:70]} ({m['from'][:30]})" for m in g["emails"]] or ["   Nothing urgent."]
    out += ["", "3. Decisions waiting on you (drafts to approve; nothing has been sent)"]
    out += [f"   {v} {k}" for k, v in g["drafts"].items()] or ["   No drafts waiting."]
    out += [f"   Late: {x.strip()}" for x in g["late"]]
    out += ["", "4. One idea", "   " + g["idea"], "", "5. One thing to watch this week", "   " + g["watch"]]
    rev = g["revenue"]
    out += ["", "6. Yesterday's revenue", f"   ${float(rev):,.2f}" if rev is not None else "   " + REV_MISSING]
    text = "\n".join(out) + "\n"
    if len(text.split()) > MAX_WORDS:
        raise ValueError("Briefing is too long; shorten the inputs.")
    return text


def save(text: str, today: date | None = None) -> Path:
    today = today or date.today()
    d = HERE / "data" / "briefings"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{today.isoformat()}.txt"
    p.write_text(text, encoding="utf-8")
    return p
