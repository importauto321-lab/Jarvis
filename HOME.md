# Home checklist (do in this order; stop and ask if anything looks different)

Nothing sends, pays, books or posts without the owner's OK. Keys and passwords never go in chat, the shared doc, or this repo.

1. Mac mini and iMac: install Python 3.11 or newer and Chrome. Get this repo (`git clone`, then `git checkout claude/jarvis-voice-responsiveness-gdzd7y`).
2. `cp leads/settings.example.json leads/settings.json`, then replace every FILL IN: business name, your name, business address, phone, reply email, service area, rate per mile, minimum charge, routes, lowest $/mile, late-day limits, review link, team emails (Nicole, Kaysha), your own email, your cell number.
3. Run `python -m leads doctor`. It lists what is still missing. Repeat until only the optional items are left.
4. Free Gemini key (aistudio.google.com): `export GEMINI_API_KEY=...` on the Mac. Never paste it in chat.
5. OpenAI (optional, when the card works): $5 credit, auto-recharge OFF, `export OPENAI_API_KEY=...`.
6. Trucking Office (read-only): export CSV files for invoices, bookings, loads, and daily numbers. Then:
   - `python -m boss import invoices invoices.csv`
   - `python -m boss import bookings bookings.csv`
   - `python -m boss import loads loads.csv`
   - `python -m boss import activity daily.csv`
   - If it says it can't find a column, send Erica the column names (customer names removed).
7. Set your goals: `python -m boss goals --quotes 30 --booked 10 --collected 12000` (use your real numbers).
8. Briefing inputs: calendar and email for the CEO briefing come from Jarvis ("give me my briefing"), or a JSON file for `python -m boss briefing --inputs`.
9. Check each load board's terms (Super Dispatch, Central Dispatch) and ask for an official API. Load boards stay OFF until then.
10. Try it: `python -m boss daily`. It builds the briefings, dashboard, and email and text DRAFTS in `boss/data/`. Read them. Send nothing yet.
11. Run in draft-only mode for one week. Review drafts with Nicole, Kaysha, and your attorney.
12. Later: schedule `python -m boss daily` each morning (Mac: `crontab -e`, line `30 6 * * * cd /path/to/Jarvis && python -m boss daily`). Always-on Managed Agents and texting (Twilio) come after this works.
