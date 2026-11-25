# Worker lists

One file per AI worker: what it does well and the rules for using it. This is the memory, so nobody
has to remember it in the moment. When the user adds an ability, add one line to that worker's file.

Make the one complete message:

    python3 tools/brief.py gemini

Check a message before handing it over:

    python3 tools/brief.py gemini --check message.txt

It prints COMPLETE only if the text of every item in the saved list and rules is in the message
(spacing and numbering don't matter). Keep the headings `## Does well` and `## Rules` as they are.
It checks against the saved list; it can't know about something that was never written down.
