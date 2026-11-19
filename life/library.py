import json
import re
from datetime import date
from pathlib import Path

DATA = Path(__file__).parent / "data"
ROUTES = ("sales", "loads", "office", "boss", "life")
STATUSES = ("pending", "approved", "rejected")


def path() -> Path:
    DATA.mkdir(exist_ok=True)
    return DATA / "library.json"


def load() -> list[dict]:
    return json.loads(path().read_text(encoding="utf-8")) if path().exists() else []


def save(rows) -> None:
    path().write_text(json.dumps(rows, indent=2), encoding="utf-8")


def add(kind: str, title: str, source: str, lessons: list[str], tags=(), route_to="life", today=None) -> dict:
    """New entries are ALWAYS pending. Nothing is used until Dee approves it."""
    if route_to not in ROUTES:
        route_to = "life"
    rows = load()
    for r in rows:
        if r["source"] and r["source"] == source and r["kind"] == kind:
            return r  # already saved
    row = {"id": max([r["id"] for r in rows] + [0]) + 1, "kind": kind, "title": title, "source": source,
           "lessons": [l.strip() for l in lessons if l.strip()], "tags": list(tags), "route_to": route_to,
           "status": "pending", "added": (today or date.today()).isoformat()}
    rows.append(row)
    save(rows)
    return row


def set_status(entry_id: int, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(status)
    rows = load()
    for r in rows:
        if r["id"] == entry_id:
            r["status"] = status
            save(rows)
            return r
    raise KeyError(f"no entry {entry_id}")


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9']+", s.lower()) if len(w) > 2}


def ask(question: str, limit: int = 5) -> list[dict]:
    """Search approved entries only. Plain word matching, free. Answers come from what was saved."""
    q = _words(question)
    scored = []
    for r in load():
        if r["status"] != "approved":
            continue
        hay = _words(" ".join([r["title"], " ".join(r["tags"]), " ".join(r["lessons"])]))
        n = len(q & hay)
        if n:
            scored.append((n, r))
    return [r for _, r in sorted(scored, key=lambda x: -x[0])[:limit]]


def for_agent(route: str) -> list[dict]:
    """Approved lessons meant for one agent (sales tips to sales, pricing ideas to loads...)."""
    return [r for r in load() if r["status"] == "approved" and r["route_to"] == route]
