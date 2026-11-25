#!/usr/bin/python3
"""The "ask me first" gate for Hermes (a ``pre_tool_call`` hook).

Hermes runs this before every tool call. It lets through a short list of things that only look,
and makes everything else wait for the owner's yes: deleting, sending, paying, running commands
that change things, writing files, code, scheduled jobs. Anything it does not recognise also asks.
Secret files are refused outright.

Browser work gets ONE yes per job: the first ordinary browser step asks for the whole job, and
later ordinary steps run on that yes. A step that looks like sending, paying, deleting, posting
or signing in asks again on its own. This is judged from the words in the step, so it can miss:
a click does not say what the button does unless the step says so.

Installed as ``~/.hermes/agent-hooks/ask_first.py`` with ``fail_closed: true``, so if this script
breaks, Hermes is blocked rather than let loose. It cannot stop every possible trick: for example
a web address that is only "read" can still carry information out.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import sys

READ_ONLY_TOOLS = {
    "web_search", "web_extract", "read_file", "search_files", "vision_analyze",
    "skill_view", "skills_list", "todo_list", "session_search",
}
# Commands that only show things. No shell tricks are allowed around them.
READ_ONLY_COMMANDS = {"ls", "cat", "head", "tail", "wc", "grep", "pwd", "date", "whoami", "uname",
                      "sw_vers", "df", "du", "stat", "which"}
# Business sites Hermes must not touch until the owner says so. Refused, not asked.
OFF_LIMITS = re.compile(r"super[\s_.\-]*dispatch|central[\s_.\-]*dispatch|trucking[\s_.\-]*office", re.IGNORECASE)
BROWSER_JOB_KEY = "ask-first:browser-job"
BROWSER_JOB_MARK = "Browse for this whole job"  # Jarvis answers this one for the whole job
# Words that mean a browser step may send, pay, delete, post or sign in: ask for that step by itself.
CONSEQUENTIAL = re.compile(
    r"(?<![a-z])(send|sent|e-?mail|message|pay|paid|payment|buy|purchase|order|checkout|check[ _-]out|donate|transfer|wire|invoice|"
    r"delete|remove|erase|trash|discard|cancel|unsubscribe|subscribe|post|publish|share|comment|reply|tweet|upload|submit|"
    r"sign[ _-]?(in|up|on)|log[ _-]?(in|on)|register|create[ _-]?account|new[ _-]?account|authori[sz]e|allow[ _-]access|"
    r"password|passcode|otp|card|cvv|cvc|confirm|accept|agree|book|reserve|apply|bid|sell|save[ _-]changes)(s|ed|ing)?(?![a-z])",
    re.IGNORECASE)
# Things a browser step could do that reach past reading and clicking.
ESCAPES = re.compile(
    r"\b(subprocess|shutil|os\.|open\s*\(|eval\s*\(|exec\s*\(|compile\s*\(|getattr|globals|locals|__\w|base64|chr\s*\(|"
    r"cdp\s*\(|upload_file|dispatch_key|fetch\s*\(|XMLHttpRequest|sendBeacon|requestSubmit|\.submit\b|WebSocket)|"
    r"press_key\s*\(\s*['\"](Enter|Return)|type_text\s*\([^)]*\\n", re.IGNORECASE)
IMPORT = re.compile(r"^\s*(from|import)\s+(?!(time|json|re)\b)", re.MULTILINE)
MAX_SHOWN = 1500
SHELL_TRICKS = re.compile(r"[;&|<>`\n\r\\]|\$[({]")
SECRETS = re.compile(
    r"\.hermes/(\.env|auth\.json|google_token|google_client_secret|shell-hooks-allowlist)|"
    r"(^|[/\s'\"=])\.env|find-(generic|internet)-password|dump-keychain|Keychains/|\.ssh/|"
    r"jarvis-openai|Hermes-for-iPad")


def is_read_only_command(command: str) -> bool:
    if not command.strip() or SHELL_TRICKS.search(command):
        return False
    try:
        words = shlex.split(command)
    except ValueError:
        return False
    if not words or words[0] not in READ_ONLY_COMMANDS:
        return False
    # Wildcards can name a secret file without spelling it, and a recursive search can read one: ask.
    if any(c in command for c in "*?[{"):
        return False
    if words[0] == "grep" and any(w == "--recursive" or w == "--dereference-recursive"
                                  or (w.startswith("-") and not w.startswith("--") and ("r" in w or "R" in w)) for w in words[1:]):
        return False
    return not any(SECRETS.search(w) or ".hermes" in w for w in words[1:])


def is_ordinary_browsing(code: str) -> bool:
    """Reading, moving around and harmless clicks: fine once the owner has said yes to the job."""
    if not code.strip() or CONSEQUENTIAL.search(code) or ESCAPES.search(code) or IMPORT.search(code):
        return False
    # A screenshot may only be written to a picture file.
    for target in re.findall(r"capture_screenshot\s*\(\s*(?:path\s*=\s*)?([^,)]*)", code):
        if target.strip() and not re.fullmatch(r"""['"][^'"]+\.png['"]|full\s*=.*|max_dim\s*=.*""", target.strip()):
            return False
    return every_click_is_explained(code)


def every_click_is_explained(code: str) -> bool:
    """Each line that clicks needs a comment right above it (or on it), so there are words to judge it by."""
    previous = ""
    for line in (part.strip() for part in code.splitlines()):
        if not line:
            continue
        if not line.startswith("#") and re.search(r"click", line, re.IGNORECASE):
            note = previous if previous.startswith("#") else line.partition("  #")[2]
            if len(re.findall(r"[A-Za-z]{2,}", note)) < 2:
                return False
        previous = line
    return True


def decide(tool: str, args: dict) -> dict:
    """``{}`` to allow, or a block / approve answer for Hermes."""
    args = args if isinstance(args, dict) else {}
    everything = json.dumps(args, sort_keys=True, default=str)
    if SECRETS.search(everything) or any(SECRETS.search(str(v)) for v in args.values()):
        return {"action": "block", "message": "Secret files and passwords are off limits."}
    if OFF_LIMITS.search(everything):
        return {"action": "block", "message": "Super Dispatch, Central Dispatch and Trucking Office are off limits for now."}
    # Quotes can split a secret's name ('.en''v'): check the words the shell would actually see.
    if tool == "terminal":
        try:
            if any(SECRETS.search(w) for w in shlex.split(str(args.get("command", "")))):
                return {"action": "block", "message": "Secret files and passwords are off limits."}
        except ValueError:
            pass
    # Hermes's own folder holds its keys: reading or searching there needs a yes.
    in_hermes = tool in {"read_file", "search_files"} and ".hermes" in everything
    if tool in READ_ONLY_TOOLS and not in_hermes:
        return {}
    if tool == "terminal" and not args.get("background") and is_read_only_command(str(args.get("command", ""))):
        return {}
    if tool == "process_manage" and args.get("action") in {"list", "poll", "log"}:
        return {}
    if tool == "browser_exec" and set(args) <= {"code", "timeout"}:
        code = str(args.get("code", ""))
        if len(code) <= MAX_SHOWN * 4 and is_ordinary_browsing(code):
            first = " ".join(code.split())[:300]
            return {"action": "approve", "rule_key": BROWSER_JOB_KEY,
                    "message": f"{BROWSER_JOB_MARK}? First step: {first}"}
    detail = str(args.get("command") or args.get("code") or everything)
    if len(detail) > MAX_SHOWN:
        # Never ask for a yes to something that can't be shown in full.
        if tool in {"terminal", "execute_code", "browser_exec"} or not args.get("path"):
            return {"action": "block", "message": "Too long to show the owner in full. Break it into smaller steps."}
        detail = f"write {len(detail)} characters to {args['path']}, starting: {detail[:300]}"
    fingerprint = hashlib.sha256((tool + everything).encode()).hexdigest()[:16]
    return {"action": "approve", "message": f"{tool}: {detail}", "rule_key": f"ask-first:{fingerprint}"}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        answer = decide(str(payload["tool_name"]), payload.get("tool_input") or {})
    except Exception:  # anything unexpected: refuse
        answer = {"action": "block", "message": "The ask-first gate could not read this request."}
    print(json.dumps(answer))
    return 0


if __name__ == "__main__":
    sys.exit(main())
