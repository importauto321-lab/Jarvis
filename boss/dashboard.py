"""Dashboard: the morning briefing, the evening summary and the invoice chaser on one screen.
One self-contained HTML file (no internet needed). Open it on the iPad. Read-only; it sends nothing."""
from datetime import date
from html import escape as e
from pathlib import Path

from leads import invoices

from . import briefing, review

HERE = Path(__file__).parent
CSS = """:root{--bg:#f6f6f4;--card:#fff;--ink:#1c1c1a;--mute:#6b6b66;--line:#e2e2dd;--warn:#b3261e;--ok:#1b6e3a}
@media(prefers-color-scheme:dark){:root{--bg:#161615;--card:#212120;--ink:#eeeeea;--mute:#a3a39d;--line:#34342f;--warn:#ff8a80;--ok:#7bd88f}}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.45 -apple-system,system-ui,sans-serif}
main{max-width:900px;margin:0 auto;padding:16px}h1{font-size:22px}h2{font-size:15px;color:var(--mute);margin:0 0 8px;text-transform:uppercase;letter-spacing:.04em}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:12px 0}
.tag{font-size:13px;font-weight:600}.u{color:var(--warn)}.ok{color:var(--ok)}pre{white-space:pre-wrap;margin:0;font:inherit}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:6px 4px;border-bottom:1px solid var(--line);font-size:15px}
.note{color:var(--mute);font-size:14px}"""


def _ul(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else "<p class=note>None.</p>"


def render(inputs: dict, activity: dict, today: date | None = None) -> str:
    today = today or date.today()
    g = briefing.gather(inputs, today)
    sample = " (SAMPLE DATA, not real)" if g["sample"] or activity.get("sample") else ""
    rev = f"${float(g['revenue']):,.2f}" if g["revenue"] is not None else briefing.REV_MISSING
    chaser = invoices.chaser_status(today)
    rows = "".join(f"<tr><td>{e(r['invoice'])}</td><td>{e(r['customer'])}</td><td>${r['amount']:,.2f}</td>"
                   f"<td>{r['days_late']}</td><td>{e(r['step'])}</td></tr>" for r in chaser)
    body = f"""<h1>Dashboard, {today:%A %B %d}{e(sample)}</h1>
<p class=note>Read-only. Nothing here sends, pays or posts. Drafts wait for your OK.</p>
<div class=card><h2>Today's calendar</h2>{_ul(f"{e(c['time'])}  {e(c['title'])}" for c in g['calendar'])}</div>
<div class=card><h2>Emails that need you</h2>{_ul(f"<span class='tag u'>{e(m['tier'])}</span> {e(m['subject'][:80])} <span class=note>({e(m['from'][:30])})</span>" for m in g['emails'])}</div>
<div class=card><h2>Decisions waiting on you</h2>{_ul(f"{v} {e(k)}" for k, v in g['drafts'].items())}</div>
<div class=card><h2>Invoice chaser</h2>{("<table><tr><th>Invoice<th>Customer<th>Amount<th>Days late<th>Next step</tr>" + rows + "</table>") if chaser else "<p class=note>No late invoices.</p>"}</div>
<div class=card><h2>One idea</h2><p>{e(g['idea'])}</p><h2>Watch this week</h2><p>{e(g['watch'])}</p></div>
<div class=card><h2>Yesterday's revenue</h2><p>{e(rev)}</p></div>
<div class=card><h2>Evening summary</h2><pre>{e(review.evening(activity, today))}</pre></div>
<div class=card><h2>Weekly roll-up</h2><pre>{e(review.weekly(activity, today))}</pre></div>"""
    return ('<!doctype html><html lang=en><head><meta charset=utf-8>'
            '<meta name=viewport content="width=device-width,initial-scale=1"><title>Business Dashboard</title>'
            f"<style>{CSS}</style></head><body><main>{body}</main></body></html>")


def save(html: str) -> Path:
    d = HERE / "data"
    d.mkdir(exist_ok=True)
    p = d / "dashboard.html"
    p.write_text(html, encoding="utf-8")
    return p
