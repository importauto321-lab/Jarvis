"""One complete instruction message per AI worker, built from the lists in ``workers/``.

``python3 tools/brief.py gemini``                   prints the full message
``python3 tools/brief.py gemini --check note.txt``  says COMPLETE, or lists what is missing
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

WORKERS = Path(__file__).resolve().parent.parent / "workers"


def names() -> list[str]:
    return sorted(p.stem for p in WORKERS.glob("*.md") if p.stem != "README")


def load(worker: str) -> dict:
    if worker not in names():
        raise ValueError(f"No saved list for '{worker}'. Saved lists: {', '.join(names())}.")
    text = (WORKERS / f"{worker}.md").read_text(encoding="utf-8")
    sections, current = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif line.startswith("- ") and current:
            sections[current].append(line[2:].strip())
    if not sections.get("Does well") or not sections.get("Rules"):
        raise ValueError(f"workers/{worker}.md needs a 'Does well' and a 'Rules' list.")
    status = re.search(r"^Wired in: (.+)$", text, re.MULTILINE)
    return {"title": text.splitlines()[0].lstrip("# ").strip(), "status": status.group(1) if status else "unknown",
            "does": sections["Does well"], "rules": sections["Rules"]}


def message(worker: str) -> str:
    w = load(worker)
    lines = [f"Wire {w['title']} into Jarvis. This is the complete list; do it all in one job.",
             f"Where it stands now: {w['status']}", "", "What it should be used for:"]
    lines += [f"{n}. {item}" for n, item in enumerate(w["does"], 1)]
    lines += ["", "Rules:"] + [f"{n}. {item}" for n, item in enumerate(w["rules"], 1)]
    lines += ["", "Test each item for real, show proof, and say plainly which ones are not done."]
    return "\n".join(lines)


def missing(worker: str, text: str) -> list[str]:
    def flat(s: str) -> str:
        return " ".join(s.lower().split())
    have = flat(text)
    w = load(worker)
    return [item for item in w["does"] + w["rules"] if flat(item) not in have]


def main(argv: list[str]) -> int:
    try:
        if len(argv) == 1:
            print(message(argv[0]))
            return 0
        if len(argv) == 3 and argv[1] == "--check":
            left_out = missing(argv[0], Path(argv[2]).read_text(encoding="utf-8"))
            if left_out:
                print("NOT COMPLETE. Missing:\n" + "\n".join("- " + item for item in left_out))
                return 1
            print(f"COMPLETE: every line of the saved {argv[0]} list is in this message.")
            return 0
    except (ValueError, OSError) as exc:
        print(exc)
        return 2
    print(f"Usage: python3 tools/brief.py <{'|'.join(names())}> [--check file]")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
