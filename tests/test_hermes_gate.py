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


@pytest.mark.parametrize("tool,args", [
    ("browser_exec", {"code": "goto('https://app.superdispatch.com/login')"}),
    ("web_extract", {"urls": ["https://www.centraldispatch.com"]}),
    ("terminal", {"command": "open https://truckingoffice.com"}),
    ("web_search", {"query": "Central Dispatch loads"}),
    ("browser_exec", {"code": "click('Trucking Office')"}),
])
def test_business_sites_are_off_limits(tool, args):
    assert hermes_gate.decide(tool, args)["action"] == "block"


@pytest.mark.parametrize("code", [
    'new_tab("https://example.com")\nwait_for_load()\nprint(page_info())',
    'print(js("document.title"))',
    '# Click the "Next page" link\nclick_at_xy(10, 20)',
    'scroll(1, 2)\nprint(capture_screenshot("/tmp/a.png"))',
    'import time\ntime.sleep(1)\ngoto_url("https://news.example.org/borders")',
])
def test_ordinary_browsing_is_one_yes_for_the_job(code):
    answer = hermes_gate.decide("browser_exec", {"code": code})
    assert answer["rule_key"] == hermes_gate.BROWSER_JOB_KEY
    assert answer["message"].startswith(hermes_gate.BROWSER_JOB_MARK)


@pytest.mark.parametrize("code", [
    '# Click the Send button\nclick_at_xy(1, 2)', '# Click Pay now\nclick_at_xy(1, 2)', '# Delete the draft\nclick_at_xy(1, 2)',
    '# Post the comment\nclick_at_xy(1, 2)', '# Sign in\nfill_input("#u", "a")', 'fill_input("#password", "x")',
    'click_at_xy(1, 2)', 'press_key("Enter")', 'type_text("hello\\n")', 'js("document.forms[0].submit()")',
    'js("fetch(\'/x\', {method: \'POST\'})")', 'import os\nos.remove("a")', 'upload_file("#f", "/etc/hosts")',
    'cdp("Input.dispatchMouseEvent")', 'capture_screenshot("/Users/a/.zshrc")', 'getattr(x, "a")', 'open("a","w")', '',
])
def test_risky_browser_steps_ask_on_their_own(code):
    answer = hermes_gate.decide("browser_exec", {"code": code})
    assert answer.get("rule_key") != hermes_gate.BROWSER_JOB_KEY
    assert answer["action"] in {"approve", "block"}


def test_other_browser_tools_and_commands_still_ask_each_time():
    for tool, args in [("browser_cdp", {"method": "x"}), ("browser_vault", {}), ("terminal", {"command": "rm a"}),
                       ("browser_exec", {"code": "print(1)", "local": True})]:
        assert hermes_gate.decide(tool, args).get("rule_key") != hermes_gate.BROWSER_JOB_KEY


def test_each_click_needs_its_own_comment():
    key = hermes_gate.BROWSER_JOB_KEY
    ask = lambda code: hermes_gate.decide("browser_exec", {"code": code}).get("rule_key")
    assert ask("# harmless note\nx = 1\nclick_at_xy(1, 2)") != key
    assert ask("# Click the Next link\nclick_at_xy(1, 2)\nclick_at_xy(3, 4)") != key
    assert ask("#\nclick_at_xy(1, 2)") != key
    assert ask("# Click the Next link\nclick_at_xy(1, 2)\n# Open the Docs tab\nclick_at_xy(3, 4)") == key
    assert ask("click_at_xy(1, 2)  # open the menu") == key
