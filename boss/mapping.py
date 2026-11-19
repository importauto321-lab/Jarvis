"""Turns a Trucking Office export (CSV, any column names) into the shapes the agent uses.
Column names are matched loosely (case, spaces, common synonyms). When the real export arrives, only the
ALIASES below might need a tweak. Read-only: it reads a file you exported."""
import csv
import json
import re
from datetime import datetime
from pathlib import Path

ALIASES = {
    "invoices": {"invoice": ["invoice", "invoice #", "invoice number", "invoice no", "inv", "inv #"],
                 "customer": ["customer", "customer name", "client", "bill to", "company"],
                 "email": ["email", "customer email", "contact email"],
                 "load": ["load", "load id", "load #", "order", "order #", "order id"],
                 "amount": ["amount", "total", "balance", "balance due", "amount due", "invoice total"],
                 "due_date": ["due date", "due", "payment due"],
                 "paid_date": ["paid date", "date paid", "paid on", "payment date"]},
    "bookings": {"customer": ["customer", "customer name", "client", "company"],
                 "route": ["route", "lane"], "pickup": ["pickup", "origin", "from"], "dropoff": ["dropoff", "delivery", "destination", "to"],
                 "car": ["car", "vehicle", "vehicle description", "year make model"],
                 "price": ["price", "total", "rate", "amount", "revenue"]},
    "loads": {"id": ["id", "load", "load id", "load #", "order #"], "status": ["status", "load status"],
              "route": ["route", "lane"], "pickup": ["pickup", "origin", "from"], "dropoff": ["dropoff", "destination", "to"]},
    "activity": {"date": ["date", "day"], "quotes_sent": ["quotes sent", "quotes"], "quotes_booked": ["quotes booked", "booked"],
                 "loads_moved": ["loads moved", "loads delivered", "delivered"],
                 "money_collected": ["money collected", "collected", "payments", "cash collected"]},
}
REQUIRED = {"invoices": ["invoice", "customer", "amount", "due_date"], "bookings": ["customer", "price"],
            "loads": ["id", "status"], "activity": ["date"]}


def _norm(h: str) -> str:
    return re.sub(r"[^a-z0-9#]+", " ", h.lower()).strip()


def date_iso(v: str) -> str:
    v = (v or "").strip()
    for f in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(v, f).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return v


def money(v: str) -> float:
    v = re.sub(r"[^0-9.\-]", "", v or "")
    return float(v) if v not in ("", "-", ".") else 0.0


def read(kind: str, src: str) -> list[dict]:
    rows = list(csv.DictReader(open(src, newline="", encoding="utf-8-sig")))
    if not rows:
        return []
    heads = {_norm(h): h for h in rows[0]}
    col = {}
    for field, names in ALIASES[kind].items():
        for n in names:
            if _norm(n) in heads:
                col[field] = heads[_norm(n)]
                break
    missing = [f for f in REQUIRED[kind] if f not in col]
    if missing:
        raise SystemExit(f"Could not find columns for: {', '.join(missing)}. Your file has: {', '.join(rows[0])}. "
                         f"Tell Erica these names and the mapping gets one small edit.")
    out = []
    for r in rows:
        o = {f: (r.get(c) or "").strip() for f, c in col.items()}
        if "pickup" in o or "dropoff" in o:
            o.setdefault("route", f"{o.get('pickup', '')} to {o.get('dropoff', '')}".strip())
        for f in ("due_date", "paid_date", "date"):
            if f in o:
                o[f] = date_iso(o[f])
        for f in ("amount", "price"):
            if f in o:
                o[f] = money(o[f])
        out.append(o)
    return out


DATA = Path(__file__).parent / "data"


def merge_json(name: str, update: dict) -> Path:
    DATA.mkdir(exist_ok=True)
    p = DATA / name
    cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    cur.update(update)
    cur.pop("sample", None)  # real data now
    p.write_text(json.dumps(cur, indent=2), encoding="utf-8")
    return p
