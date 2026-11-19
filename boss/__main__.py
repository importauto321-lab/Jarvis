"""python -m boss briefing | evening | weekly | dashboard. Writes files or prints. Sends nothing."""
import argparse
from datetime import date

import csv
import tempfile

from leads import invoices

from . import briefing, dashboard, deliver, mapping, review, team_briefing


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="boss")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, h in (("briefing", "today's CEO briefing"), ("evening", "end-of-day summary against your goals"),
                    ("weekly", "weekly roll-up: what went well, what to fix"),
                    ("dashboard", "one-screen HTML page with all of it"),
                    ("team", "Nicole and Kaysha day-to-day briefing (draft file, not sent)")):
        s = sub.add_parser(name, help=h)
        s.add_argument("--inputs", help="briefing JSON (default: pretend sample)")
        s.add_argument("--activity", help="daily numbers JSON (default: pretend sample)")
        s.add_argument("--date", help="YYYY-MM-DD (default: today)")
    im = sub.add_parser("import", help="read a Trucking Office export (CSV) into real data")
    im.add_argument("kind", choices=["invoices", "bookings", "loads", "activity"]); im.add_argument("file")
    go = sub.add_parser("goals", help="set your weekly goals")
    go.add_argument("--quotes", type=float); go.add_argument("--booked", type=float); go.add_argument("--collected", type=float)
    dl = sub.add_parser("daily", help="build everything for today: briefings, dashboard, email and text DRAFTS (sends nothing)")
    dl.add_argument("--date")
    args = ap.parse_args(argv)
    if args.cmd == "import":
        rows = mapping.read(args.kind, args.file)
        if args.kind == "invoices":
            tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8")
            w = csv.DictWriter(tmp, fieldnames=["invoice", "customer", "email", "load", "amount", "due_date", "paid_date"], extrasaction="ignore")
            w.writeheader(); w.writerows(rows); tmp.close()
            print(f"{invoices.import_csv(tmp.name)} invoices imported.")
        elif args.kind == "activity":
            cur = review.load() if (mapping.DATA / "activity.json").exists() else {"days": []}
            by = {d["date"]: d for d in cur["days"]}
            for r in rows:
                by[r["date"]] = {k: (mapping.money(str(v)) if k != "date" else v) for k, v in r.items()}
            print("Saved", mapping.merge_json("activity.json", {"days": sorted(by.values(), key=lambda d: d["date"])}))
        else:
            print("Saved", mapping.merge_json("team.json", {args.kind: rows}), f"({len(rows)} {args.kind})")
        return 0
    if args.cmd == "goals":
        goals = {k: v for k, v in (("weekly_quotes", args.quotes), ("weekly_booked", args.booked), ("weekly_collected", args.collected)) if v}
        cur = review.load() if (mapping.DATA / "activity.json").exists() else {"days": []}
        print("Saved", mapping.merge_json("activity.json", {"days": cur.get("days", []), "goals": {**cur.get("goals", {}), **goals}}))
        return 0
    if args.cmd == "daily":
        today = date.fromisoformat(args.date) if args.date else date.today()
        inputs, act, team = briefing.load_inputs(), review.load(), team_briefing.load()
        made = [briefing.save(briefing.build(inputs, today), today),
                dashboard.save(dashboard.render(inputs, act, today)),
                team_briefing.save_draft(team_briefing.build(team, today), today)]
        for label, fn in (("owner email", lambda: deliver.email_draft("owner", f"Briefing {today:%b %d}", briefing.build(inputs, today), today)),
                          ("team email", lambda: deliver.email_draft("team", f"Team briefing {today:%b %d}", team_briefing.build(team, today), today)),
                          ("text", lambda: deliver.text_draft(deliver.short_text(inputs, today), today))):
            try:
                made.append(fn())
            except SystemExit as e:
                print(f"Skipped {label}: {e}")
        print("Built (nothing sent):"); [print(" ", p) for p in made]
        return 0
    today = date.fromisoformat(args.date) if args.date else date.today()
    if args.cmd == "briefing":
        text = briefing.build(briefing.load_inputs(args.inputs), today)
        print(text); print("Saved to", briefing.save(text, today), "(not sent anywhere)")
    elif args.cmd == "team":
        text = team_briefing.build(team_briefing.load(args.inputs), today)
        print(text); print("Draft saved to", team_briefing.save_draft(text, today), "(not sent)")
    elif args.cmd == "evening":
        print(review.evening(review.load(args.activity), today))
    elif args.cmd == "weekly":
        print(review.weekly(review.load(args.activity), today))
    else:
        p = dashboard.save(dashboard.render(briefing.load_inputs(args.inputs), review.load(args.activity), today))
        print("Dashboard saved to", p, "(open it in a browser; nothing is sent)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
