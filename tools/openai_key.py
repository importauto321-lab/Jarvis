"""Keep the OpenAI key in the macOS Keychain. It is never printed, saved in this folder, or put on a command line.

Run ``python3 tools/openai_key.py`` and paste the key once at the hidden prompt.
``python3 tools/openai_key.py --repair`` fixes a saved key that was pasted more than once.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

SERVICE = "jarvis-openai"
KEY_RE = re.compile(r"^sk-[A-Za-z0-9_\-]{20,}$")


def read_key(run=subprocess.run) -> str:
    """The key from OPENAI_API_KEY or the Keychain, or "" if there is none."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    try:
        out = run(["security", "find-generic-password", "-s", SERVICE, "-w"], capture_output=True, text=True)
    except OSError:
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def save_key(key: str, run=subprocess.run) -> None:
    if len(pieces(key)) > 1:
        raise ValueError("The key was pasted more than once (nothing shows while pasting). Run this again and paste it one time.")
    if not KEY_RE.match(key):
        raise ValueError("That doesn't look like an OpenAI key. It starts with sk- and has no spaces.")
    # Sent on standard input, so the key never shows up in the list of running programs.
    command = f'add-generic-password -U -a "{getpass.getuser()}" -s {SERVICE} -w "{key}"\n'
    run(["security", "-i"], input=command, capture_output=True, text=True)
    if read_key_from_keychain(run) != key:
        raise ValueError("The Mac did not save the key. Nothing was stored.")


def read_key_from_keychain(run=subprocess.run) -> str:
    out = run(["security", "find-generic-password", "-s", SERVICE, "-w"], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def list_models(key: str, post=None) -> list[str]:
    req = urllib.request.Request("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"})
    with (post or urllib.request.urlopen)(req, timeout=30) as r:
        return [m["id"] for m in json.load(r)["data"]]


def pieces(text: str) -> list[str]:
    """The separate keys inside a pasted line: one normally, more if it was pasted repeatedly."""
    starts = [m.start() for m in re.finditer(r"sk-(?:proj|svcacct|admin)-", text)]
    if not starts:
        return [text]
    return [text[a:b] for a, b in zip(starts, starts[1:] + [len(text)])]


def repair(run=subprocess.run, check=list_models) -> str:
    """Keep the one copy OpenAI accepts out of a key that was saved several times over."""
    saved = read_key_from_keychain(run)
    if len(pieces(saved)) < 2:
        return "The saved key is not doubled up, so there is nothing to repair."
    for candidate in dict.fromkeys(pieces(saved)):
        try:
            check(candidate)
        except urllib.error.HTTPError:
            continue
        except urllib.error.URLError as exc:
            return f"Could not reach OpenAI ({exc.reason}). Nothing was changed."
        save_key(candidate, run)
        return "Repaired. One copy is saved and OpenAI accepted it."
    return "OpenAI accepted none of the copies. Nothing was changed."


def main(argv=()) -> int:
    if "--repair" in argv:
        message = repair()
        print(message)
        return 0 if message.startswith("Repaired") else 1
    key = getpass.getpass("Paste your OpenAI key ONE time, then press Return (nothing will show): ").strip()
    try:
        save_key(key)
    except ValueError as exc:
        print(exc)
        return 1
    print("Saved in your Mac's Keychain.")
    subprocess.run(["pbcopy"], input="", text=True)  # take the key off the clipboard
    print("I cleared your clipboard.")
    try:
        list_models(key)  # free: only checks that OpenAI accepts the key
        print("OpenAI accepted the key.")
    except urllib.error.HTTPError as exc:
        print(f"OpenAI refused the key (error {exc.code}). Make a new key and run this again.")
        return 1
    except urllib.error.URLError as exc:
        print(f"Could not reach OpenAI to check it ({exc.reason}).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
