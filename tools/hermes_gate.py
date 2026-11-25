#!/usr/bin/python3
"""The "ask me first" gate for Hermes (a ``pre_tool_call`` hook).

Hermes runs this before every tool call. It lets through a short list of things that only look,
and makes everything else wait for the owner's yes: deleting, sending, paying, running commands
that change things, writing files, code, clicks in the browser, scheduled jobs. Anything it does
not recognise also asks. Secret files are refused outright.

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
MAX_SHOWN = 1500
SHELL_TRICKS = re.compile(r"[;&|<>`\n\r\\]|\$[({]")
SECRETS = re.compile(
    r"\.hermes/(\.env|auth\.json|google_token|google_client_secret|shell-hooks-allowlist)|"
    r"(^|[/\s'\"=])\.env(\b|$)|find-(generic|internet)-password|dump-keychain|Keychains/|\.ssh/|"
    r"jarvis-openai|Hermes-for-iPad")


def is_read_only_command(command: str) -> bool:
    if not command.strip() or SHELL_TRICKS.search(command):
        return False
    try:
        words = shlex.split(command)
    except ValueError:
        return False
    return bool(words) and words[0] in READ_ONLY_COMMANDS


def decide(tool: str, args: dict) -> dict:
    """``{}`` to allow, or a block / approve answer for Hermes."""
    args = args if isinstance(args, dict) else {}
    everything = json.dumps(args, sort_keys=True, default=str)
    if SECRETS.search(everything) or any(SECRETS.search(str(v)) for v in args.values()):
        return {"action": "block", "message": "Secret files and passwords are off limits."}
    if tool in READ_ONLY_TOOLS:
        return {}
    if tool == "terminal" and not args.get("background") and is_read_only_command(str(args.get("command", ""))):
        return {}
    if tool == "process_manage" and args.get("action") in {"list", "poll", "log"}:
        return {}
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
