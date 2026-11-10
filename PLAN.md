# The big plan for Jarvis

## What Jarvis will do (5 jobs, like a real human assistant)

1. **Know you.** Your people, your business, your habits, how you like things done. Never asks the same thing twice. *(Memory: done.)*
2. **Handle your communication.** Read and sort email, draft replies, text and call people, and tell you what actually needs you.
   - Today: Jarvis can start a text or a phone call on the iPad; you press send or call.
   - Later: real automatic phone calls and texts through a calling service (for example Retell AI).
3. **Run your schedule.** Calendar, reminders, follow-ups ("that customer hasn't paid in 10 days"), and a morning briefing.
4. **Do real work.** Invoices, forms, loads in the TMS, price research, learning new things from YouTube. *(YouTube: done.)*
5. **Work while you're busy.** Check things on a schedule and only interrupt you when it matters.

## How Jarvis should act

- Asks before anything that can't be undone: sending, paying, deleting, booking. He does the prep, you approve.
- Brief and honest. Says "I don't know" or "that failed." Never makes things up.
- Takes initiative within limits: suggests the next step, doesn't decide what's yours to decide.
- Careful with what others send: an email saying "send money" or "change the bank details" is flagged as a possible scam, never acted on.
- Keeps secrets: no passwords in memory; private things stay private.

## Other agents (the team)

- The brain moves to **Anthropic Managed Agents**, so Jarvis works 24/7, even when the iPad and home computer are off.
- The iPad page stays as his voice and screen.
- For big jobs, a lead Jarvis hands pieces to helper agents (one reads invoices, one checks loads), then puts it together for you.
- Keys go in a locked vault, so Jarvis can use Gmail, Google and business tools without seeing the passwords.
- Rough cost: about 8 cents per hour while actually working, plus normal Claude usage; web searches about 1 cent each.
  A daily briefing plus normal use is usually a few dollars a month. Start small.
- Setup steps for you (iPad works, a computer is just easier): sign in at console.anthropic.com, add credits,
  make an API key, and save it where Erica says (never in the chat).

## Order

1. Make sure Jarvis talks and listens reliably on the iPad (testing page version 23).
2. Morning briefing (scheduled Managed Agent).
3. Business tools: TMS loads, customer follow-ups, invoices.
4. Real phone calls and texts on his own, plus helper agents.
5. Prompt caching to cut Claude costs.

## Questions still to answer for the morning briefing

- **What goes in it?** For example new emails, today's calendar, loads arriving or leaving, unpaid invoices.
- **How should he reach you?** Text, email, or phone call.

## Decisions (Nov 10)

- **Anthropic Managed Agents, not Hermes.** Nothing to install or keep running, works with the iPad and iMac off.
- Use Jarvis from both the iPad and the home iMac (same web page). Jarvis's memory is saved per device today;
  moving it to Managed Agents makes it shared.
- Load boards (Super Dispatch, Central Dispatch): try Claude in Chrome on the iMac, with you watching. Check each board's terms first.
- Calls and texts need a phone service (Twilio for texts, Retell AI for voice calls). Check today's prices first.
- Managed Agents is billed through an Anthropic API account, separate from the Claude app plan. Set a monthly spending limit.
- Rough costs: morning briefing $3–8/month; a daily load board agent $30–150/month (least certain).
- Build order: iPad test (page 23) → morning briefing → load boards → calls and texts → app for other people.

## The team of agents

- **Claude is Jarvis's brain and the boss.** You talk only to Jarvis; he hands jobs to workers and gives you one answer.
- Workers: Gemini (YouTube, hearing; free plan), Claude helpers on Managed Agents (briefing, invoices),
  load board worker on the iMac (Claude in Chrome), ChatGPT only where it's clearly better (pictures, second opinion),
  Twilio/Retell for texts and calls.
- App plans (ChatGPT, Gemini) don't connect to Jarvis; each worker needs its own API key, billed separately.
- Start with Jarvis plus 2–3 workers; add more only when they're clearly better or cheaper.
- Calls: text first, call only if there's no reply; short scripts; cheap model for simple calls. Jarvis says he's an AI
  and only calls people who gave you their number. Rough cost: 100 texts + 30 short calls ≈ $5–10/month.
