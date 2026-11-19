"""python -m life add-video URL --live | add-book | list | approve | reject | ask | for. Nothing here sends anything."""
import argparse

from . import engine, library


def show(r):
    print(f"#{r['id']} [{r['status']}] {r['kind']}: {r['title']} -> {r['route_to']}")
    for l in r["lessons"]:
        print("    -", l)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="life")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("add-video", help="have Gemini watch a YouTube link and propose lessons (needs --live)")
    v.add_argument("url"); v.add_argument("--live", action="store_true")
    b = sub.add_parser("add-book", help="save a book and your key lessons from it")
    b.add_argument("title"); b.add_argument("--author", default="")
    b.add_argument("--lesson", action="append", default=[], help="one lesson; repeat for more")
    b.add_argument("--route", default="life", choices=library.ROUTES)
    sub.add_parser("list", help="show everything saved, with status")
    for n in ("approve", "reject"):
        sub.add_parser(n).add_argument("id", type=int)
    a = sub.add_parser("ask", help="answer from approved entries only"); a.add_argument("question", nargs="+")
    f = sub.add_parser("for", help="approved lessons for one agent"); f.add_argument("agent", choices=library.ROUTES)
    args = ap.parse_args(argv)
    if args.cmd == "add-video":
        if not args.live:
            print("Dry run: nothing watched. Add --live when you want it to run."); return 0
        r = engine.learn_video(args.url); show(r); print("Saved as PENDING. Approve it if it is right: python -m life approve", r["id"])
    elif args.cmd == "add-book":
        r = library.add("book", args.title, args.author, args.lesson, route_to=args.route)
        show(r); print("Saved as PENDING. Approve with: python -m life approve", r["id"])
    elif args.cmd == "list":
        for r in library.load(): show(r)
    elif args.cmd in ("approve", "reject"):
        show(library.set_status(args.id, "approved" if args.cmd == "approve" else "rejected"))
    elif args.cmd == "ask":
        hits = library.ask(" ".join(args.question))
        if not hits: print("Nothing approved in the library matches that.")
        for r in hits: show(r)
    elif args.cmd == "for":
        for r in library.for_agent(args.agent): show(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
