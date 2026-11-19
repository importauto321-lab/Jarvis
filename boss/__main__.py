"""python -m boss briefing [--inputs FILE]. Writes a file. Sends nothing."""
import argparse

from . import briefing


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="boss")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("briefing", help="build today's CEO briefing")
    b.add_argument("--inputs", help="JSON file (default: pretend sample data)")
    args = ap.parse_args(argv)
    text = briefing.build(briefing.load_inputs(args.inputs))
    print(text)
    print("Saved to", briefing.save(text), "(not sent anywhere)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
