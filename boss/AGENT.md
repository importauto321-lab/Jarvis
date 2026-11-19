# Boss agent (Phase 1): CEO morning briefing

Ready to be plugged in; nothing here runs live. Draft-only: it writes a briefing, never sends, pays, books or posts.

## What it does each morning
Builds the same six-part briefing (under 3 minutes): calendar and deadlines, emails that need Dee, drafts waiting
for his OK, one idea, one thing to watch, yesterday's revenue. Code: `boss/briefing.py`. Try it: `python -m boss briefing`.

## Status
- Works now on PRETEND data (`boss/sample/inputs.json`). The output says SAMPLE DATA.
- Email ranking and draft counts reuse the business agent (`leads/`).

## To plug in at the house (Dee away until about Nov 25, so none of this is done)
1. Calendar and Gmail: read-only access, to fill `calendar` and `emails` in the inputs file.
2. Revenue: read-only access to Trucking Office (the TMS).
3. Delivery: text, email or the Jarvis page is UNDECIDED. Until then the briefing is only saved as a file.
4. Always-on: run it on a schedule through Anthropic Managed Agents. NOT built or tested. I have not verified how
   Managed Agents scheduling works for this account, so that step needs a short test first.
5. Nicole and Kaysha get a separate briefing (Phase 3). Not part of this.

## Rules
Nothing risky happens without Dee's OK. Gmail and Calendar are read-only here. Keys and passwords never go in files in this repo.
