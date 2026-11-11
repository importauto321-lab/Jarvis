"""Load boards: Super Dispatch and Central Dispatch.

NOTHING here logs in, scrapes or posts. Reasons:
  1. Their terms may not allow automation. A human checks each board's terms first.
  2. Both boards may offer an official API. Ask each for it before anyone considers a browser robot.

Until then the only supported input is a CSV you export or copy from the board (see loads.py).
`ALLOWED` stays False until the owner writes "load_boards_allowed": true in settings.json
AND someone has written a connector below. Even then, searching is the most it may do:
no accepting, booking, bidding or posting without the owner's OK.
"""
import json

from . import drafts

BOARDS = ("Super Dispatch", "Central Dispatch")


def allowed() -> bool:
    if not drafts.SETTINGS.exists():
        return False
    return json.loads(drafts.SETTINGS.read_text(encoding="utf-8")).get("load_boards_allowed") is True


def search(board: str, routes):
    if not allowed():
        raise SystemExit("Load board search is OFF. Export loads to a CSV and use: python -m leads loads FILE")
    raise SystemExit(f"No {board} connector is built yet. Do that only after the board's terms are checked.")
