"""Invoice chaser, demand letters and review requests. ALL DRAFT-ONLY.

Invoices come from a CSV you export (columns: invoice, customer, email, load, amount, due_date, paid_date).
Dates are YYYY-MM-DD. A blank paid_date means unpaid.
"""
import csv
from datetime import date, datetime, timedelta
from pathlib import Path

from . import drafts, store

COLS = ["invoice", "customer", "email", "load", "amount", "due_date", "paid_date",
        "reminder_drafted", "demand_drafted", "review_drafted"]
DEMAND_DIR = "demand_letters"


def path() -> Path:
    store.DATA.mkdir(exist_ok=True)
    return store.DATA / "invoices.csv"


def load() -> list[dict]:
    return list(csv.DictReader(path().open(newline="", encoding="utf-8"))) if path().exists() else []


def save(rows):
    with path().open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore", restval="")
        w.writeheader(); w.writerows(rows)


def import_csv(src: str) -> int:
    """Merge your export in. Keeps our drafted-marks for invoices we already know."""
    old = {r["invoice"]: r for r in load()}
    rows = []
    for r in csv.DictReader(open(src, newline="", encoding="utf-8-sig")):
        r = {k.strip().lower(): (v or "").strip() for k, v in r.items()}
        if not r.get("invoice"):
            continue
        keep = old.get(r["invoice"], {})
        for c in ("reminder_drafted", "demand_drafted", "review_drafted"):
            r[c] = keep.get(c, "")
        rows.append(r)
    save(rows)
    return len(rows)


def days_late(r, today) -> int:
    if r.get("paid_date") or not r.get("due_date"):
        return 0
    return (today - datetime.strptime(r["due_date"], "%Y-%m-%d").date()).days


def _sig(s):
    return f"{s['your_name']}\n{s['business_name']}\n{s['phone']} | {s['reply_email']}\n{s['business_address']}"


def reminder(r, s, late) -> str:
    return (f"To: {r['email'] or '(no email on file)'}\nSubject: Friendly reminder: invoice {r['invoice']}\n\n"
            f"Hi {r['customer']},\n\nA quick reminder that invoice {r['invoice']} for load {r['load']} "
            f"(${float(r['amount']):,.2f}) was due {r['due_date']} and is now {late} days past due. "
            f"If it's already on its way, thank you and please ignore this. "
            f"If anything is holding it up, just reply and let me know.\n\nThanks,\n{_sig(s)}\n")


def demand(r, s, late, today) -> str:
    deadline = today + timedelta(days=int(s["payment_deadline_days"]))
    return (f"*** DRAFT. NOT SENT. NOT YET APPROVED BY {s['attorney_name']} ***\n"
            f"To: {r['email'] or '(no email on file)'}\nSubject: Payment demand: invoice {r['invoice']}\n\n"
            f"{r['customer']},\n\nOur records show invoice {r['invoice']} for load {r['load']}, "
            f"in the amount of ${float(r['amount']):,.2f}, was due on {r['due_date']} and remains unpaid "
            f"({late} days past due).\n\nPayment in full must be received by {deadline:%B %d, %Y}. "
            f"If we do not receive it by then, we will consider further collection options.\n\n"
            f"If you believe this is an error, contact me right away at {s['phone']} or {s['reply_email']}.\n\n"
            f"Sincerely,\n{_sig(s)}\n")


def review(r, s) -> str:
    return (f"To: {r['email'] or '(no email on file)'}\nSubject: Thank you, {r['customer']}\n\n"
            f"Hi {r['customer']},\n\nThank you for your payment on invoice {r['invoice']} and for trusting us "
            f"with your car. If we did a good job, a short Google review would mean a lot:\n{s['google_review_link']}\n\n"
            f"Thanks again,\n{_sig(s)}\n")


def run(kind: str, today: date | None = None) -> list[Path]:
    """kind: chase | demand | review. Writes drafts, marks the invoice so it is never drafted twice."""
    today = today or date.today()
    need = ["your_name", "business_name", "business_address", "phone", "reply_email"]
    need += {"chase": ["reminder_days_late"], "demand": ["demand_days_late", "payment_deadline_days", "attorney_name"],
             "review": ["google_review_link"]}[kind]
    s = drafts.load_settings(need)
    rows, out = load(), []
    outdir = store.DATA / "invoice_drafts" / kind
    outdir.mkdir(parents=True, exist_ok=True)
    for r in rows:
        late = days_late(r, today)
        if kind == "chase" and late >= int(s["reminder_days_late"]) and not r["reminder_drafted"] and not r["demand_drafted"]:
            text, mark = reminder(r, s, late), "reminder_drafted"
        elif kind == "demand" and late >= int(s["demand_days_late"]) and not r["demand_drafted"]:
            text, mark = demand(r, s, late, today), "demand_drafted"
        elif kind == "review" and r.get("paid_date") and not r["review_drafted"]:
            text, mark = review(r, s), "review_drafted"
        else:
            continue
        p = outdir / f"{r['invoice']}.txt"
        p.write_text(text, encoding="utf-8")
        r[mark] = today.isoformat()
        out.append(p)
    save(rows)
    return out


def unpaid_report(today: date | None = None) -> list[str]:
    today = today or date.today()
    late = [(days_late(r, today), r) for r in load()]
    return [f"{d:>4} days late  {r['invoice']}  {r['customer']}  ${float(r['amount']):,.2f}"
            for d, r in sorted(late, key=lambda x: -x[0]) if d > 0]
