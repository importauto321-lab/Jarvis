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
    seen = {}
    reply = {"body": {"choices": [{"message": {"content": "It is done. Two things changed."}, "finish_reason": "stop"}]},
             "status": 200}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["path"] = self.path
            seen["auth"] = self.headers.get("Authorization")
            seen["payload"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(reply["status"])
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(reply["body"]).encode())

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}", seen, reply
    srv.shutdown()


def test_ask_sends_task_with_key_and_draft_only_rules(server):
    url, seen, _ = server
    assert hermes.ask("check the inbox", url=url, key="secret") == "It is done. Two things changed."
    assert seen["path"] == "/v1/chat/completions"
    assert seen["auth"] == "Bearer secret"
    msgs = seen["payload"]["messages"]
    assert msgs[1] == {"role": "user", "content": "check the inbox"}
    assert "Draft only" in msgs[0]["content"] and "spoken" in msgs[0]["content"]


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
    reply["body"] = {"nope": 1}
    with pytest.raises(hermes.HermesError, match="expect"):
        hermes.ask("hi", url=url, key="k")
    reply["body"] = {"choices": [{"message": {"content": "x"}, "finish_reason": "error"}]}
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
    reply["body"] = {"choices": [{"message": {"content": "Your inbox has three new emails."}, "finish_reason": "stop"}]}
    a, speaker = make_assistant(tmp_path, url)
    assert a.respond("Ask Hermes to check my inbox.") == "Your inbox has three new emails."
    assert speaker.said == ["Sending that to Hermes."]
    assert seen["payload"]["messages"][1]["content"] == "check my inbox"


def test_long_answer_points_to_screen(server, tmp_path, monkeypatch, capsys):
    url, _, reply = server
    monkeypatch.setenv("JARVIS_HERMES_KEY", "k")
    reply["body"] = {"choices": [{"message": {"content": "One. Two. Three. Four. Five."}, "finish_reason": "stop"}]}
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
