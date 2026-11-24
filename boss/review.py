"""Review agent: nightly check of what went well and what did not, plus a weekly roll-up. Blunt on purpose.

Numbers come from a JSON file of daily activity (quotes sent and booked, loads moved, money collected, why deals
were lost) and Dee's goals. Pretend data until the real numbers are plugged in. Reads numbers, sends nothing.
"""
from __future__ import annotations
import json
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
KEYS = ("quotes_sent", "quotes_booked", "loads_moved", "money_collected")


def load(path: str | None = None) -> dict:
    return json.loads(Path(path or (HERE / "data" / "activity.json" if (HERE / "data" / "activity.json").exists() else HERE / "sample" / "activity.json")).read_text(encoding="utf-8"))


def _sum(days) -> dict:
    t = {k: sum(float(d.get(k, 0)) for d in days) for k in KEYS}
    lost: dict = {}
    for d in days:
        for why, n in d.get("lost", {}).items():
            lost[why] = lost.get(why, 0) + n
    t["lost"] = lost
    return t


def _rate(booked, sent) -> str:
    return f"{100 * booked / sent:.0f}%" if sent else "n/a"


def _leak(lost: dict) -> str:
    if not lost:
        return "No lost deals logged."
    why, n = max(lost.items(), key=lambda x: x[1])
    return f"Biggest leak: '{why}' ({n:.0f} of {sum(lost.values()):.0f} lost deals)."


def evening(data: dict, today: date) -> str:
    days = data.get("days", [])
    d = next((x for x in days if x["date"] == today.isoformat()), None)
    week = [x for x in days if today - timedelta(days=6) <= date.fromisoformat(x["date"]) <= today]
    w, g = _sum(week), data.get("goals", {})
    lines = [f"EVENING SUMMARY, {today:%A %B %d}" + ("  [SAMPLE DATA, not real]" if data.get("sample") else "")]
    if d:
        t = _sum([d])
        lines += ["", "Today",
                  f"  Quotes sent {t['quotes_sent']:.0f}, booked {t['quotes_booked']:.0f} ({_rate(t['quotes_booked'], t['quotes_sent'])}), "
                  f"loads moved {t['loads_moved']:.0f}, collected ${t['money_collected']:,.0f}.",
                  "  " + _leak(t["lost"])]
    else:
        lines += ["", "Today", "  No activity logged for today. Either nothing happened or nobody logged it."]
    lines += ["", "On track for the week? (last 7 days)"]
    for label, got, goal in (("Quotes sent", w["quotes_sent"], g.get("weekly_quotes")),
                             ("Loads booked", w["quotes_booked"], g.get("weekly_booked")),
                             ("Money collected", w["money_collected"], g.get("weekly_collected"))):
        if goal:
            pct = 100 * got / goal
            verdict = "ON TRACK" if pct >= 100 else "BEHIND"
            lines.append(f"  {label}: {got:,.0f} of {goal:,.0f} ({pct:.0f}%) {verdict}")
        else:
            lines.append(f"  {label}: {got:,.0f} (no goal set. Dee names the goals.)")
    return "\n".join(lines) + "\n"


def weekly(data: dict, today: date) -> str:
    week = [x for x in data.get("days", []) if today - timedelta(days=6) <= date.fromisoformat(x["date"]) <= today]
    w = _sum(week)
    wins = []
    if w["quotes_sent"] and round(100 * w["quotes_booked"] / w["quotes_sent"]) >= 30:
        wins.append("Booking rate is 30% or better.")
    if w["money_collected"]:
        wins.append(f"Collected ${w['money_collected']:,.0f}.")
    fixes = [_leak(w["lost"])]
    if w["quotes_sent"] and round(100 * w["quotes_booked"] / w["quotes_sent"]) < 30:
        fixes.append(f"Only {_rate(w['quotes_booked'], w['quotes_sent'])} of quotes became loads. Quotes are going out and dying.")
    zero = [x["date"] for x in week if not x.get("money_collected")]
    if zero:
        fixes.append("No money collected on: " + ", ".join(zero) + ".")
    lines = [f"WEEKLY ROLL-UP, week ending {today:%B %d}" + ("  [SAMPLE DATA, not real]" if data.get("sample") else ""), "",
             f"Quotes sent {w['quotes_sent']:.0f}, booked {w['quotes_booked']:.0f} ({_rate(w['quotes_booked'], w['quotes_sent'])}), "
             f"loads moved {w['loads_moved']:.0f}, collected ${w['money_collected']:,.0f}.", "", "What went well"]
    lines += [f"  {x}" for x in wins] or ["  Nothing clear yet."]
    lines += ["", "What to fix"] + [f"  {x}" for x in fixes]
    return "\n".join(lines) + "\n"
