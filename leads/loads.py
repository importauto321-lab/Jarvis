"""Load matcher and load builder. Works on loads YOU bring in (CSV copied/exported from Super Dispatch or
Central Dispatch). It does not log in to or scrape any board. See boards.py.

Loads CSV columns: id, source, pickup, dropoff, miles, price, vehicle, pickup_date (YYYY-MM-DD).
pickup/dropoff look like "Dallas, TX".
"""
import csv
from datetime import datetime

FIELDS = ["id", "source", "pickup", "dropoff", "miles", "price", "vehicle", "pickup_date"]


def load_csv(path: str) -> list[dict]:
    rows = []
    for r in csv.DictReader(open(path, newline="", encoding="utf-8-sig")):
        r = {k.strip().lower(): (v or "").strip() for k, v in r.items()}
        if r.get("id"):
            rows.append(r)
    return rows


def state(place: str) -> str:
    return place.rsplit(",", 1)[-1].strip().upper() if "," in place else place.strip().upper()


def _hit(place: str, want: str) -> bool:
    want = want.strip().upper()
    return want == state(place) or want in place.upper()


def per_mile(l: dict) -> float:
    m = float(l.get("miles") or 0)
    return float(l["price"]) / m if m else 0.0


def match(loads, routes, min_per_mile=0.0, both_ways=True) -> list[dict]:
    """routes: [{"from": "TX", "to": "FL"}]. A route is a state or a city name. Best $/mile first."""
    out = []
    for l in loads:
        for r in routes:
            fwd = _hit(l["pickup"], r["from"]) and _hit(l["dropoff"], r["to"])
            back = both_ways and _hit(l["pickup"], r["to"]) and _hit(l["dropoff"], r["from"])
            if fwd or back:
                ppm = per_mile(l)
                if ppm >= min_per_mile:
                    out.append({**l, "per_mile": round(ppm, 2), "route": f"{r['from']}-{r['to']}"})
                break
    return sorted(out, key=lambda x: -x["per_mile"])


def build_truck(loads, capacity=9, window_days=5, origin_state: str | None = None) -> list[dict]:
    """Suggest a set of matched loads for one truck: same corridor, pickups within a few days, up to
    `capacity` cars, best $/mile first. A starting suggestion only: a human checks it."""
    if not loads:
        return []
    first = loads[0]
    corridor = first["route"]
    d0 = datetime.strptime(first["pickup_date"], "%Y-%m-%d") if first.get("pickup_date") else None
    plan, cars = [], 0
    for l in loads:
        if l["route"] != corridor:
            continue
        if d0 and l.get("pickup_date"):
            if abs((datetime.strptime(l["pickup_date"], "%Y-%m-%d") - d0).days) > window_days:
                continue
        n = max(1, int(l.get("cars") or 1))
        if cars + n > capacity:
            continue
        plan.append(l); cars += n
    return plan


def summary(plan) -> str:
    if not plan:
        return "No loads fit."
    total = sum(float(l["price"]) for l in plan)
    miles = max(float(l.get("miles") or 0) for l in plan)
    lines = [f"  {l['id']} ({l['source']}) {l['pickup']} -> {l['dropoff']} {l['vehicle']} ${float(l['price']):,.0f} (${l['per_mile']}/mi)"
             for l in plan]
    return "\n".join(lines + [f"{len(plan)} cars, ${total:,.0f} total, about ${total / miles:,.2f}/mile over {miles:,.0f} miles" if miles else ""])
