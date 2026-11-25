# Jarvis: start-to-finish plan (researched 11/25/2026)

Goal: speak a job on the phone or iPad, the home iMac does it (browser and files), spreadsheets and
documents come back to the phone, several AIs help, and nothing is sent, paid or deleted without a yes.

## The best existing apps

| | Claude app (Cowork + Dispatch) | OpenClaw | Perplexity Personal Computer |
|---|---|---|---|
| Cost | Pro $20/month ($17 yearly), already paid | Free software; pay for AI use (one blog estimates $10-30/month light, $100+ heavy) | Not on its page; articles say $200 Max, one says $20 Pro (unconfirmed) |
| Jobs from phone | Yes | Yes, iOS app | Yes, iPhone |
| Works the browser | Yes, its own | Yes (blog and docs listings) | Yes, with its Comet browser |
| Files to phone | Yes | Download of attachments | Reads and writes files; sending to phone not stated |
| Voice | Voice mode exists; not stated for Cowork tasks | Talk mode and wake word | Voice input |
| Several AIs | Claude only | Any | 20+ |
| Scheduled jobs | Yes | Yes | Not stated |
| Main drawback | Dispatch is limited beta, closed to new users; cloud tasks do not touch the iMac | You maintain and secure it; past exposed-setup incidents | Price unclear; needs Comet |

Also looked at: Manus "My Computer" (about $20-40/month, sources differ). Hermes Agent, which is
already installed here, includes Telegram chat with voice memos, sending spreadsheets as
attachments, and scheduled jobs.

## What Jarvis has

Voice on the iPad, Claude with Gemini and ChatGPT, Hermes for the iMac and browser, approval before
risky steps, email attachment reading, an always-on iMac.

## What Jarvis is missing

1. Spreadsheets and documents made on request and delivered to the phone.
2. Scheduled jobs (morning report, renewal reminders) with nobody there.
3. A notification on the phone when a job finishes or needs a yes.
4. Jobs that keep going when the Jarvis page is closed or the screen sleeps.
5. Hands-free wake word.
6. One memory shared by iPad, voice and Hermes.
7. Proof on the real iPad for the newest features.

## Decision

Do not build items 1-3 from scratch. Hermes already has them. Keep Jarvis as the iPad voice, and add
Hermes's built-in Telegram connection as the phone channel. Do not switch to OpenClaw (same kind of
tool as Hermes) or buy Perplexity now.

## The plan

Each step is finished only when its test passes on the real device.

| # | Step | Done when | You do |
|---|---|---|---|
| 0 | Prove what is built | On the iPad: Hermes job, Gemini search, ChatGPT second opinion, email attachment, one browser job with approval | Run five sentences |
| 1 | Try the Claude app you already pay for (1 hour) | One spreadsheet made from the phone; note whether Dispatch is offered | Open the Claude app |
| 2 | Lock down and back up the iMac first | Time Machine backup made and one file restored; screen locks when idle; you know how to stop Hermes; a missed morning job gets noticed | Plug in a backup drive |
| 3 | Phone channel: Hermes on Telegram | Voice memo from the phone gets an answer; an approval prompt arrives and "no" stops the job; only your account can talk to it | Create the bot, paste its token at a hidden prompt |
| 4 | Files to phone | "Make a spreadsheet of our trucks and trailers" arrives as .xlsx and opens | Open it |
| 5 | Scheduled work | A morning message arrives two days in a row: today's calendar, emails needing you, expiring registrations | Pick the time |
| 6 | Write down what Hermes may read and keep; then Gmail, Calendar, Drive, one at a time | Reads and drafts only; sending still asks | Sign in to Google and click Allow |
| 7 | Finding loads | A daily list matching your routes, rate and what the trailers can carry; you book | Routes, lowest rate, empty weights; ask each load board what it allows |
| 8 | Business tools | Quotes, invoice follow-ups, as drafts | Approve each send |
| 9 | Calls and texts (last) | Only after 0-8 run for two weeks | Approve cost first |

## Second opinion (ChatGPT, 11/25/2026)

It agreed with not buying or switching yet. It warned that Telegram is a weak place for approvals,
customer information and business files: if the bot token or chat is exposed, someone could send jobs
or read files. It also asked for backups and lock-down first, said shared memory is not simple, and said
AI costs can exceed the estimate. Changes made: backups and lock-down moved before Telegram.

**Telegram limits:** only your account may talk to the bot; no customer details, VINs, banking or
sensitive files through it (those stay on the private Tailscale connection); if that is not acceptable,
skip step 3 and keep to the iPad page.

Shared memory: not promised. Until then, a shared notes file is the realistic version.

## Rules for every step

- Ask before anything that sends, pays, deletes, posts or logs into a new account.
- Super Dispatch, Central Dispatch and Trucking Office stay blocked until you say.
- No cards or banking logins in Hermes's browser.
- Set monthly limits at console.anthropic.com and platform.openai.com; auto-recharge off.
- Test, send changes to the ChatGPT checker, show proof.

## Rough monthly cost

Claude Pro $20 (already), iMac electricity $5-10, AI use by Jarvis and Hermes about $10-45 depending
on the number of jobs (estimate), Telegram and Tailscale free on personal use.

## Sources

https://claude.com/product/cowork, https://claude.com/pricing,
https://support.claude.com/en/articles/13947068, https://docs.openclaw.ai/,
https://docs.openclaw.ai/nodes/talk, https://www.perplexity.ai/personal-computer,
https://hermes-agent.nousresearch.com/
