"""python -m leads <command>. Nothing here sends email."""
import argparse
import sys

from . import drafts, finder, inbox, invoices, quotes, ranking, store


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="leads", description="Car hauling lead list (draft-only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="add a lead")
    a.add_argument("name"); a.add_argument("kind", choices=store.KINDS)
    a.add_argument("--city", default=""); a.add_argument("--website", default="")
    a.add_argument("--email", default=""); a.add_argument("--phone", default="")
    a.add_argument("--ships", default="unknown", help="yes/no/unknown: do they ship cars?")
    a.add_argument("--notes", default="")
    sub.add_parser("rank", help="score and list leads, best first")
    sub.add_parser("draft", help="write email drafts to leads/data/drafts (does NOT send)")
    s = sub.add_parser("status", help="set a lead's status (approved, sent, replied, ...)")
    s.add_argument("id"); s.add_argument("status", choices=store.STATUSES)
    f = sub.add_parser("find", help="search the web for leads (needs --live and GEMINI_API_KEY)")
    f.add_argument("kind", choices=store.KINDS); f.add_argument("area")
    f.add_argument("--live", action="store_true", help="really call Gemini (off by default)")
    r_ = sub.add_parser("research", help="research one lead more (needs --live)")
    r_.add_argument("id"); r_.add_argument("--live", action="store_true")
    k = sub.add_parser("keep", help="OK candidate leads so they can get drafts")
    k.add_argument("ids", nargs="+")
    q = sub.add_parser("quote", help="quote = miles x your rate per mile")
    q.add_argument("pickup"); q.add_argument("dropoff"); q.add_argument("car")
    q.add_argument("--miles", type=float, help="miles, if you know them")
    q.add_argument("--live", action="store_true", help="look up miles on the free OpenStreetMap map")
    ii = sub.add_parser("invoices", help="import | unpaid | chase | demand | review")
    ii.add_argument("action", choices=["import", "unpaid", "chase", "demand", "review"])
    ii.add_argument("file", nargs="?")
    ib = sub.add_parser("inbox", help="suggest an order for an exported mailbox (.mbox, folder of .eml, or .json)")
    ib.add_argument("file"); ib.add_argument("--out", help="also save the report to this file")
    sub.add_parser("list", help="show the reply tracker")
    args = ap.parse_args(argv)

    if args.cmd == "add":
        r = store.add(dict(name=args.name, kind=args.kind, city_state=args.city, website=args.website,
                           email=args.email, phone=args.phone, ships_cars=args.ships, notes=args.notes))
        print(f"Lead {r['id']}: {r['name']}")
    elif args.cmd == "find":
        if not args.live:
            print("Dry run: nothing searched. Add --live when you want it to run."); return 0
        for r in finder.find(args.kind, args.area):
            print(f"candidate #{r['id']}: {r['name']} ({r['city_state']}) ships={r['ships_cars']}")
        print("Look them over, then: python -m leads keep <ids>")
    elif args.cmd == "research":
        if not args.live:
            print("Dry run: nothing searched. Add --live."); return 0
        r = finder.research(args.id); print(f"#{r['id']} {r['name']}: ships={r['ships_cars']} {r['notes']}")
    elif args.cmd == "keep":
        for i in args.ids:
            r = store.update(i, status="new"); print(f"kept #{r['id']} {r['name']}")
    elif args.cmd == "quote":
        st = drafts.load_settings(["rate_per_mile", "minimum_charge"])
        miles = args.miles
        if miles is None:
            if not args.live:
                print("Give --miles N, or add --live to look the miles up."); return 0
            miles = quotes.road_miles(args.pickup, args.dropoff)
        print(quotes.quote(miles, args.car, st)["text"], f"({args.pickup} to {args.dropoff})")
        print("This is a suggestion. Check it before you send it.")
    elif args.cmd == "invoices":
        if args.action == "import":
            print(f"{invoices.import_csv(args.file)} invoices imported.")
        elif args.action == "unpaid":
            print("\n".join(invoices.unpaid_report()) or "No late invoices.")
        else:
            made = invoices.run(args.action)
            print(f"{len(made)} drafts written. Nothing is sent." + (" Attorney must approve demand letters." if args.action == "demand" else ""))
            for p in made: print(" ", p)
    elif args.cmd == "inbox":
        import json as _j
        owners = {}
        if drafts.SETTINGS.exists():
            owners = _j.loads(drafts.SETTINGS.read_text(encoding="utf-8")).get("inbox_owners", {})
        text = inbox.report(inbox.sort_messages(inbox.load_messages(args.file), owners))
        print(text)
        if args.out:
            open(args.out, "w", encoding="utf-8").write(text)
    elif args.cmd == "rank":
        rows = ranking.rank(store.load()); store.save(rows)
        for r in rows:
            print(f"{r['score']:>3}  #{r['id']}  {r['name']} ({r['kind']}, {r['city_state']})")
    elif args.cmd == "draft":
        made = drafts.write_drafts()
        print(f"{len(made)} drafts written. Read them, then nothing is sent until you send it yourself.")
        for p in made:
            print(" ", p)
    elif args.cmd == "status":
        r = store.update(args.id, status=args.status)
        print(f"#{r['id']} {r['name']} -> {r['status']}")
    elif args.cmd == "list":
        for r in store.load():
            print(f"#{r['id']:<3} {r['status']:<15} {r['name']} ({r['kind']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
