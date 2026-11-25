import datetime as dt
import io
import json
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from jarvis import hermes
from jarvis.assistant import Assistant
from jarvis.config import Config
from jarvis.skills import Context


class Speaker:
    def __init__(self):
        self.said = []

    def say(self, text):
        self.said.append(text)


def make_assistant(tmp_path, url="http://127.0.0.1:1", timeout=5):
    config = Config(hermes_url=url, hermes_timeout=timeout, notes_file=tmp_path / "n.txt")
    speaker = Speaker()
    ctx = Context(config=config, speaker=speaker, open_url=lambda u: None, now=lambda: dt.datetime(2026, 11, 24, 9, 0))
    return Assistant(config, None, speaker, None, ctx), speaker


@pytest.fixture
def server():
    """A pretend Hermes. ``reply`` controls it; ``seen`` records what Jarvis sent."""
    seen = {"approvals": []}
    reply = {"output": "It is done. Two things changed.", "status": 200, "final": "completed",
             "asks": [], "start": {"run_id": "run_1"}}

    class H(BaseHTTPRequestHandler):
        def send(self, body):
            self.send_response(reply["status"])
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen["auth"] = self.headers.get("Authorization")
            if self.path.endswith("/approval"):
                seen["approvals"].append(payload)
                reply["asks"].pop(0)
                return self.send({})
            if self.path.endswith("/stop"):
                seen["stopped"] = True
                return self.send({})
            seen["path"], seen["payload"] = self.path, payload
            self.send(reply["start"])

        def do_GET(self):
            if reply["asks"]:
                return self.send({"status": "waiting_for_approval", "pending_controls": [reply["asks"][0]]})
            self.send({"status": reply["final"], "output": reply["output"]})

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}", seen, reply
    srv.shutdown()


def ask_card(n, what):
    return {"kind": "approval", "prompt_id": f"p{n}", "execution_generation": 1, "description": what}


def test_ask_sends_task_with_key_and_rules(server):
    url, seen, _ = server
    assert hermes.ask("check the inbox", url=url, key="secret") == "It is done. Two things changed."
    assert seen["path"] == "/v1/runs"
    assert seen["auth"] == "Bearer secret"
    assert seen["payload"]["input"] == "check the inbox"
    assert "asks the owner" in seen["payload"]["instructions"] and "spoken" in seen["payload"]["instructions"]


def test_each_permission_request_is_asked_and_answered(server):
    url, seen, reply = server
    reply["asks"] = [ask_card(1, "rm a"), ask_card(2, "send mail")]
    asked = []
    hermes.ask("x", url=url, key="k", approve=lambda w: asked.append(w) or w == "rm a", sleep=lambda s: None)
    assert asked == ["rm a", "send mail"]
    assert [a["choice"] for a in seen["approvals"]] == ["once", "deny"]
    assert seen["approvals"][0] == {"choice": "once", "request_id": "p1", "execution_generation": 1}


def test_with_no_way_to_ask_the_answer_is_no(server):
    url, seen, reply = server
    reply["asks"] = [ask_card(1, "rm a")]
    hermes.ask("x", url=url, key="k", sleep=lambda s: None)
    assert seen["approvals"][0]["choice"] == "deny"


def test_too_slow_runs_are_stopped(server):
    url, seen, reply = server
    reply["final"] = "running"
    ticks = iter(range(0, 1000, 100))
    with pytest.raises(hermes.HermesError, match="stop"):
        hermes.ask("x", url=url, key="k", timeout=250, sleep=lambda s: None, clock=lambda: next(ticks))
    assert seen["stopped"]


@pytest.mark.parametrize("said,expected", [("yes", True), ("Jarvis, yes.", True), ("yes, go ahead", True),
                                           ("no", False), ("yes but wait", False), ("", False), (None, False),
                                           ("yesterday", False)])
def test_only_a_clear_yes_allows(tmp_path, said, expected):
    a, _ = make_assistant(tmp_path)
    a.listener = type("L", (), {"listen": lambda self: said})()
    assert a.context.confirm("May I?") is expected


def test_ask_needs_a_key(monkeypatch, tmp_path):
    monkeypatch.delenv("JARVIS_HERMES_KEY", raising=False)
    monkeypatch.setattr(hermes, "DEFAULT_ENV_FILE", tmp_path / "missing.env")
    with pytest.raises(hermes.HermesError, match="key"):
        hermes.ask("hi", url="http://127.0.0.1:1")


def test_read_key_from_env_var_then_file(monkeypatch, tmp_path):
    f = tmp_path / ".env"
    f.write_text("OTHER=1\nAPI_SERVER_KEY='abc123'\n")
    monkeypatch.delenv("JARVIS_HERMES_KEY", raising=False)
    assert hermes.read_key(f) == "abc123"
    monkeypatch.setenv("JARVIS_HERMES_KEY", "fromenv")
    assert hermes.read_key(f) == "fromenv"


@pytest.mark.parametrize("code,word", [(401, "key"), (500, "500")])
def test_http_errors_become_speakable_messages(server, code, word):
    url, _, reply = server
    reply["status"] = code
    with pytest.raises(hermes.HermesError, match=word):
        hermes.ask("hi", url=url, key="k")


def test_unreachable_hermes_says_to_open_the_app():
    def boom(req, timeout=0):
        raise urllib.error.URLError("refused")
    with pytest.raises(hermes.HermesError, match="Open the Hermes app"):
        hermes.ask("hi", key="k", post=boom)


def test_odd_reply_and_failed_run(server):
    url, _, reply = server
    reply["start"] = {"nope": 1}
    with pytest.raises(hermes.HermesError, match="expect"):
        hermes.ask("hi", url=url, key="k")
    reply["start"], reply["final"] = {"run_id": "r"}, "failed"
    with pytest.raises(hermes.HermesError, match="couldn't finish"):
        hermes.ask("hi", url=url, key="k")


def test_speakable_cleans_markdown_and_shortens():
    text = "## Result\n- **Sent** the [report](https://x.example/a)\n- Saw https://y.example now\nOne. Two. Three. Four."
    spoken, shortened = hermes.speakable(text)
    assert "*" not in spoken and "#" not in spoken and "http" not in spoken and "](" not in spoken
    assert "a link" in spoken or "report" in spoken
    assert shortened
    assert hermes.speakable("All good.") == ("All good.", False)
    assert hermes.speakable("```x```") == ("Done.", False)


def test_voice_command_routes_to_hermes_and_speaks_answer(server, tmp_path, monkeypatch):
    url, seen, reply = server
    monkeypatch.setenv("JARVIS_HERMES_KEY", "k")
    reply["output"] = "Your inbox has three new emails."
    a, speaker = make_assistant(tmp_path, url)
    assert a.respond("Ask Hermes to check my inbox.") == "Your inbox has three new emails."
    assert speaker.said == ["Sending that to Hermes."]
    assert seen["payload"]["input"] == "check my inbox"


def test_long_answer_points_to_screen(server, tmp_path, monkeypatch, capsys):
    url, _, reply = server
    monkeypatch.setenv("JARVIS_HERMES_KEY", "k")
    reply["output"] = "One. Two. Three. Four. Five."
    a, _ = make_assistant(tmp_path, url)
    out = a.respond("tell hermes that I need a summary")
    assert out.endswith("The full answer is on the screen.")
    assert "Five." in capsys.readouterr().out


def test_voice_command_reports_problem_instead_of_crashing(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HERMES_KEY", "k")
    a, _ = make_assistant(tmp_path, "http://127.0.0.1:1")
    assert "Hermes" in a.respond("have hermes look into the loads")


def test_other_commands_still_work(tmp_path):
    a, _ = make_assistant(tmp_path)
    assert "4" in a.respond("what is 2 plus 2")


def test_the_actual_command_is_always_shown():
    assert hermes.what_is_asked({"description": "delete in root path", "command": "rm /x/y"}) == "delete in root path: rm /x/y"
    assert hermes.what_is_asked({"description": "terminal: rm a", "command": "<terminal> (plugin approval rule)"}) == "terminal: rm a"
    assert hermes.what_is_asked({}) == "something it did not describe"


def test_a_browsing_yes_covers_the_job_and_others_are_once(server):
    url, seen, reply = server
    reply["asks"] = [ask_card(1, hermes.BROWSER_JOB_MARK + "? First step: x"), ask_card(2, "browser_exec: click Pay")]
    hermes.ask("x", url=url, key="k", approve=lambda w: True, sleep=lambda s: None)
    assert [a["choice"] for a in seen["approvals"]] == ["session", "once"]
