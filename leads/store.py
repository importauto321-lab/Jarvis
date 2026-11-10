"""Simple lead list kept in leads/data/leads.csv (opens in Excel/Numbers)."""
import csv
from pathlib import Path

DATA = Path(__file__).parent / "data"
FIELDS = ["id", "name", "kind", "city_state", "website", "email", "phone",
          "ships_cars", "notes", "score", "status", "last_update"]
KINDS = ("dealer", "auction", "broker")
# new -> drafted -> approved -> sent (you mark sent by hand) -> replied / no_reply / not_interested
STATUSES = ("new", "drafted", "approved", "sent", "replied", "no_reply", "not_interested")


def path() -> Path:
    DATA.mkdir(exist_ok=True)
    return DATA / "leads.csv"


def load() -> list[dict]:
    p = path()
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(rows: list[dict]) -> None:
    with path().open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def add(row: dict) -> dict:
    rows = load()
    key = (row.get("name", "").strip().lower(), row.get("city_state", "").strip().lower())
    for r in rows:
        if (r["name"].strip().lower(), r["city_state"].strip().lower()) == key:
            return r  # already have it
    row = {f: row.get(f, "") for f in FIELDS}
    row["id"] = str(max([int(r["id"]) for r in rows] + [0]) + 1)
    row["status"] = row["status"] or "new"
    rows.append(row)
    save(rows)
    return row


def update(lead_id: str, **changes) -> dict:
    rows = load()
    for r in rows:
        if r["id"] == str(lead_id):
            if "status" in changes and changes["status"] not in STATUSES:
                raise ValueError(f"status must be one of {STATUSES}")
            r.update({k: str(v) for k, v in changes.items() if k in FIELDS})
            save(rows)
            return r
    raise KeyError(f"no lead {lead_id}")
