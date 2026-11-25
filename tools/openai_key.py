"""Keep the OpenAI key in the macOS Keychain. It is never printed, saved in this folder, or put on a command line.

Run ``python3 tools/openai_key.py`` and paste the key at the hidden prompt.
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


def main() -> int:
    key = getpass.getpass("Paste your OpenAI key, then press Return (nothing will show): ").strip()
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
    sys.exit(main())
