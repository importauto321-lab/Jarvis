"""Nicole and Kaysha's day-to-day briefing: bookings, loads, invoices, unpaid balances, urgent email.
Until the app exists it goes by email or text. This only builds the text and a Gmail-ready draft file.
It never sends. Dee decides what goes to them (this is a first version)."""
import json
from datetime import date
from pathlib import Path

from leads import inbox, invoices

from . import briefing

HERE = Path(__file__).parent


def load(path: str | None = None) -> dict:
    return json.loads(Path(path or HERE / "sample" / "team.json").read_text(encoding="utf-8"))


def build(data: dict, today: date | None = None) -> str:
    today = today or date.today()
    out = [f"TEAM BRIEFING, {today:%A %B %d}" + ("  [SAMPLE DATA, not real]" if data.get("sample") else "")]
    out += ["", "1. New bookings"]
    out += [f"   {b['customer']}: {b['car']}, {b['route']}, ${float(b['price']):,.0f}" for b in data.get("bookings", [])] or ["   None."]
    out += ["", "2. Loads in motion"]
    out += [f"   {l['id']}: {l['status']} ({l['route']})" for l in data.get("loads", [])] or ["   None."]
    late = invoices.chaser_status(today)
    out += ["", "3. Invoices and unpaid balances"]
    out += [f"   {r['invoice']} {r['customer']} ${r['amount']:,.2f}, {r['days_late']} days late: {r['step']}" for r in late] or ["   No late invoices."]
    total = sum(r["amount"] for r in late)
    if late:
        out.append(f"   Total late: ${total:,.2f}")
    out += ["", "4. Urgent email first"]
    urgent = [m for m in inbox.sort_messages(data.get("emails", []), today=today) if m["tier"] == "URGENT"][:5]
    out += [f"   {m['subject'][:70]} ({m['from'][:30]})" for m in urgent] or ["   Nothing urgent."]
    out += ["", "Drafts wait for Dee's OK. Nothing is sent without it."]
    return "\n".join(out) + "\n"


def save_draft(text: str, today: date | None = None) -> Path:
    """Writes subject + body to a file, ready to paste into an email. Not sent."""
    today = today or date.today()
    d = HERE / "data" / "team"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{today.isoformat()}.txt"
    p.write_text(f"Subject: Team briefing {today:%b %d}\n\n{text}", encoding="utf-8")
    return p
