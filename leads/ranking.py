"""Rank leads 0-100 from simple, explainable signs. No AI needed."""

KIND_POINTS = {"broker": 25, "auction": 20, "dealer": 15}


def score(lead: dict) -> int:
    pts = KIND_POINTS.get(lead.get("kind", ""), 5)
    ships = (lead.get("ships_cars") or "").lower()
    if ships in ("yes", "y", "true"):
        pts += 35
    elif ships in ("maybe", "unknown", ""):
        pts += 10
    if lead.get("email"):
        pts += 20
    if lead.get("phone"):
        pts += 5
    if lead.get("website"):
        pts += 5
    if lead.get("notes"):
        pts += 10  # we researched it
    return min(pts, 100)


def rank(rows: list[dict]) -> list[dict]:
    for r in rows:
        r["score"] = str(score(r))
    return sorted(rows, key=lambda r: -int(r["score"]))
