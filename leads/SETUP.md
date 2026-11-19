# Business agent: how the pieces fit (draft-only)

One agent, three sections. Each section only DRAFTS or SUGGESTS. Nothing is sent, paid, booked or posted without the owner's OK.

| Section | Jobs | Command |
|---|---|---|
| Sales | find leads, research, rank, draft emails, reply tracker, review requests | find, research, keep, rank, draft, status, list, invoices review |
| Loads | quotes, load matching, truck suggestions | quote, loads |
| Office | invoice reminders, demand letters (attorney approves), inbox sorter | invoices import/unpaid/chase/demand, inbox |

## Boss and workers (from PLAN.md)
- **Boss: Claude.** Reads the plan, decides which section runs, checks the drafts, asks you for OK.
- **Researcher: Gemini** (free plan). Used by `find` and `research`.
- **Checker: ChatGPT.** Second opinion on big decisions (see CHECKER below).
- **Hands: Claude in Chrome on the Mac mini.** Only for board work, and only after each board's terms are checked.
- **iMac:** your workstation. Runs the same commands and holds the reports.

## CHECKER (ChatGPT)
Ask it for a second opinion before: a demand letter goes out, a quote far from your rate, or any big money decision.
It only reviews text you give it, and answers "agree / disagree and why". It never acts.
Needs an OpenAI key (platform.openai.com, $5 credit, auto-recharge OFF). Key goes in a file or environment
variable at home, never in chat or email. Code for this is written on Day 6.

## Load boards
`boards.py` is OFF. Today: export or copy loads to a CSV and run `python -m leads loads loads.csv`.
Before any automation: read each board's terms, ask each for an official API, and test with you watching.
