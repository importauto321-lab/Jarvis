"""python -m boss briefing | evening | weekly | dashboard. Writes files or prints. Sends nothing."""
import argparse
from datetime import date

from . import briefing, dashboard, review


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="boss")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, h in (("briefing", "today's CEO briefing"), ("evening", "end-of-day summary against your goals"),
                    ("weekly", "weekly roll-up: what went well, what to fix"),
                    ("dashboard", "one-screen HTML page with all of it")):
        s = sub.add_parser(name, help=h)
        s.add_argument("--inputs", help="briefing JSON (default: pretend sample)")
        s.add_argument("--activity", help="daily numbers JSON (default: pretend sample)")
        s.add_argument("--date", help="YYYY-MM-DD (default: today)")
    args = ap.parse_args(argv)
    today = date.fromisoformat(args.date) if args.date else date.today()
    if args.cmd == "briefing":
        text = briefing.build(briefing.load_inputs(args.inputs), today)
        print(text); print("Saved to", briefing.save(text, today), "(not sent anywhere)")
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
