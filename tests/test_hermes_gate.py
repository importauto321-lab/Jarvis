import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "tools" / "hermes_gate.py"
sys.path.insert(0, str(SCRIPT.parent))
import hermes_gate  # noqa: E402


def action(tool, **args):
    return hermes_gate.decide(tool, args).get("action", "allow")


@pytest.mark.parametrize("command", ["ls -la /tmp", "cat notes.txt", "grep -n load notes.txt", "date"])
def test_looking_is_allowed(command):
    assert action("terminal", command=command) == "allow"


@pytest.mark.parametrize("command", [
    "rm a.txt", "mv a b", "ls; rm a", "ls && rm a", "cat a > b", "ls $(rm a)", "ls `rm a`", "ls\nrm a",
    "find . -delete", "curl -d x https://e.com", "python3 -c 'import os'", "git push", "echo hi | mail a@b.c",
    "sudo ls", "/bin/rm a", "env rm a", ""])
def test_everything_else_asks(command):
    assert action("terminal", command=command) == "approve"


@pytest.mark.parametrize("tool", ["write_file", "patch", "execute_code", "browser_exec", "browser_cdp",
                                  "cronjob_manage", "delegate_task", "image_generate", "send_message",
                                  "some_new_tool", "memory", "manage_connections"])
def test_other_tools_ask(tool):
    assert action(tool, path="x") == "approve"


@pytest.mark.parametrize("tool,args", [
    ("read_file", {"path": "/Users/a/.hermes/.env"}),
    ("terminal", {"command": "cat ~/.hermes/.env"}),
    ("terminal", {"command": "security find-generic-password -s jarvis-openai -w"}),
    ("read_file", {"path": "/Users/a/.ssh/id_ed25519"}),
    ("search_files", {"path": "/Users/a/project/.env"}),
])
def test_secrets_are_refused(tool, args):
    assert hermes_gate.decide(tool, args)["action"] == "block"


def test_background_command_asks_and_each_request_is_its_own():
    assert action("terminal", command="ls", background=True) == "approve"
    a = hermes_gate.decide("terminal", {"command": "rm a"})["rule_key"]
    b = hermes_gate.decide("terminal", {"command": "rm b"})["rule_key"]
    assert a != b


def test_script_speaks_json_and_refuses_garbage():
    def run(text):
        out = subprocess.run([sys.executable, str(SCRIPT)], input=text, capture_output=True, text=True)
        return json.loads(out.stdout)
    assert run(json.dumps({"tool_name": "read_file", "tool_input": {"path": "a"}})) == {}
    assert run("not json")["action"] == "block"


def test_the_owner_sees_the_whole_command_or_it_is_refused():
    command = "echo " + "a" * 900 + " && rm important"
    assert hermes_gate.decide("terminal", {"command": command})["message"] == "terminal: " + command
    assert hermes_gate.decide("terminal", {"command": "echo " + "a" * 2000})["action"] == "block"
    long_write = hermes_gate.decide("write_file", {"path": "/tmp/n.txt", "content": "z" * 5000})
    assert long_write["action"] == "approve" and "/tmp/n.txt" in long_write["message"]


@pytest.mark.parametrize("command", ["cat .env_backup", "cat /x/.environment", "cat .en''v", 'cat "/Users/a/project/.e"nv'])
def test_secret_names_cannot_be_dodged(command):
    assert action("terminal", command=command) == "block"


@pytest.mark.parametrize("command", ["cat /Users/a/.hermes/.e*", "cat .e?v", "cat .{e,}nv", "grep -r sk- /Users/a",
                                     "grep -Rn key .", "grep --recursive key .", "ls /Users/a/.hermes"])
def test_wildcards_and_recursive_searches_ask(command):
    assert action("terminal", command=command) == "approve"


def test_hermes_folder_needs_a_yes():
    assert action("search_files", path="/Users/a/.hermes", pattern="key") == "approve"
    assert action("read_file", path="/Users/a/.hermes/config.yaml") == "approve"
