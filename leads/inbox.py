"""Inbox sorter. SUGGESTS an order only. It reads a file and writes a report; it never touches the mailbox.

Input: a Google Takeout .mbox file, a folder of .eml files, or a .json list of
{"from","subject","body","date"}. Rules-based, so it costs $0 to run.
"""
import json
import mailbox
import re
from email import policy
from email.parser import BytesParser
from pathlib import Path

from . import invoices, store

URGENT = {"urgent": 5, "asap": 5, "past due": 5, "overdue": 5, "damage": 6, "damaged": 6, "claim": 5,
          "dispute": 5, "attorney": 5, "lawsuit": 6, "insurance": 3, "cancel": 4, "cancellation": 4,
          "delivery": 3, "pickup": 3, "pick up": 3, "dispatch": 3, "tomorrow": 3, "today": 3,
          "payment": 3, "invoice": 2, "quote": 2, "late": 2, "stuck": 4, "missing": 3, "bol": 2}
JUNK = ("unsubscribe", "newsletter", "no-reply", "noreply", "promotion", "% off", "webinar", "sale ends")


def _text(msg) -> dict:
    body = msg.get_body(preferencelist=("plain", "html"))
    text = body.get_content() if body else ""
    return {"from": str(msg["from"] or ""), "subject": str(msg["subject"] or ""),
            "body": re.sub(r"\s+", " ", text)[:2000], "date": str(msg["date"] or "")}


def load_messages(src: str) -> list[dict]:
    p = Path(src)
    if p.is_dir():
        return [_text(BytesParser(policy=policy.default).parse(f.open("rb"))) for f in sorted(p.glob("*.eml"))]
    if p.suffix == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    out = []
    for m in mailbox.mbox(str(p)):
        out.append(_text(BytesParser(policy=policy.default).parsebytes(m.as_bytes())))
    return out


def known_addresses() -> set[str]:
    a = {r["email"].lower() for r in store.load() if r.get("email")}
    a |= {r["email"].lower() for r in invoices.load() if r.get("email")}
    return a


def late_addresses(today=None) -> set[str]:
    from datetime import date
    today = today or date.today()
    return {r["email"].lower() for r in invoices.load() if r.get("email") and invoices.days_late(r, today) > 0}


def score(m: dict, known=frozenset(), late=frozenset(), owners=None) -> dict:
    hay = f"{m['subject']} {m['body']}".lower()
    sender = m["from"].lower()
    pts, why = 0, []
    for k, w in URGENT.items():
        if k in hay:
            pts += w; why.append(k)
    if any(k in sender for k in known) and known:
        pts += 3; why.append("known contact")
    if any(k in sender for k in late) and late:
        pts += 5; why.append("owes us money")
    if any(j in hay or j in sender for j in JUNK):
        pts -= 8; why.append("looks like junk")
    owner = "Unassigned"
    for name, words in (owners or {}).items():
        if any(w.lower() in hay for w in words):
            owner = name; break
    tier = "URGENT" if pts >= 8 else "TODAY" if pts >= 3 else "CAN WAIT" if pts > -3 else "JUNK?"
    return {**m, "points": pts, "tier": tier, "owner": owner, "why": sorted(set(why))[:4]}


def sort_messages(msgs, owners=None, today=None) -> list[dict]:
    known, late = known_addresses(), late_addresses(today)
    scored = [score(m, known, late, owners) for m in msgs]
    return sorted(scored, key=lambda m: -m["points"])


def report(sorted_msgs) -> str:
    lines = ["INBOX SUGGESTION (nothing was moved, deleted or sent)", ""]
    for tier in ("URGENT", "TODAY", "CAN WAIT", "JUNK?"):
        group = [m for m in sorted_msgs if m["tier"] == tier]
        lines.append(f"== {tier} ({len(group)}) ==")
        for m in group:
            lines.append(f"  [{m['owner']}] {m['subject'][:70]}  | {m['from'][:40]}  | {', '.join(m['why']) or '-'}")
        lines.append("")
    return "\n".join(lines)
