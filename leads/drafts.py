"""Write email drafts to files. This module has NO sending code, on purpose."""
import json
from pathlib import Path

from . import store

SETTINGS = Path(__file__).parent / "settings.json"
DRAFTS = store.DATA / "drafts"
PLACEHOLDER = "FILL IN"


def load_settings(need=None) -> dict:
    if not SETTINGS.exists():
        raise SystemExit("Missing leads/settings.json. Copy settings.example.json to settings.json and fill it in.")
    s = json.loads(SETTINGS.read_text(encoding="utf-8"))
    missing = [k for k, v in s.items() if PLACEHOLDER in str(v) and (need is None or k in need)]
    if missing:
        raise SystemExit("Fill in these settings first: " + ", ".join(missing))
    return s


def compose(lead: dict, s: dict, opener: str = "") -> str:
    """Plain, personal email. `opener` is one researched sentence about them."""
    kind = {"dealer": "dealership", "auction": "auction", "broker": "brokerage"}.get(lead["kind"], "business")
    opener = opener or lead.get("notes", "").split(".")[0].strip()
    first = f"{opener}. " if opener else ""
    body = (
        f"Hi {lead['name']} team,\n\n"
        f"{first}I'm {s['your_name']} with {s['business_name']}. {s['one_line_pitch']} "
        f"We cover {s['service_area']}, and I'd like to see if we can help your {kind} move cars.\n\n"
        f"If it's useful, reply with a lane or a vehicle and I'll send a quote the same day. "
        f"Or call me at {s['phone']}.\n\n"
        f"Thanks,\n{s['your_name']}\n{s['business_name']}\n{s['phone']} | {s['reply_email']}\n\n"
        f"--\n{s['business_name']}, {s['business_address']}\n"
        f"Don't want to hear from us? Reply \"unsubscribe\" and we won't email you again."
    )
    return f"To: {lead.get('email') or '(no email found)'}\nSubject: Car hauling for {lead['name']}\n\n{body}\n"


def write_drafts(only_status: str = "new") -> list[Path]:
    s = load_settings()
    DRAFTS.mkdir(parents=True, exist_ok=True)
    out = []
    for lead in store.load():
        if lead["status"] != only_status or not lead.get("email"):
            continue
        p = DRAFTS / f"{int(lead['id']):03d}_{lead['name'].replace('/', '-')[:40]}.txt"
        p.write_text(compose(lead, s), encoding="utf-8")
        store.update(lead["id"], status="drafted")
        out.append(p)
    return out
