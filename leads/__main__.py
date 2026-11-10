"""python -m leads <command>. Nothing here sends email."""
import argparse
import sys

from . import drafts, ranking, store


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
    sub.add_parser("list", help="show the reply tracker")
    args = ap.parse_args(argv)

    if args.cmd == "add":
        r = store.add(dict(name=args.name, kind=args.kind, city_state=args.city, website=args.website,
                           email=args.email, phone=args.phone, ships_cars=args.ships, notes=args.notes))
        print(f"Lead {r['id']}: {r['name']}")
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
