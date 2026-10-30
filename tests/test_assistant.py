import datetime as dt

import pytest

from jarvis.assistant import Assistant
from jarvis.config import Config
from jarvis.skills import Context, Exit, safe_eval, to_expression


class RecordingSpeaker:
    def __init__(self):
        self.said = []

    def say(self, text):
        self.said.append(text)


class ScriptedListener:
    def __init__(self, lines):
        self.lines = list(lines)

    def listen(self):
        return self.lines.pop(0) if self.lines else None


class FakeBrain:
    def __init__(self):
        self.questions = []

    def ask(self, question):
        self.questions.append(question)
        return "brain answer"


@pytest.fixture
def make(tmp_path):
    def build(lines=(), brain=None, require_wake_word=True):
        config = Config(require_wake_word=require_wake_word, notes_file=tmp_path / "notes.txt")
        speaker = RecordingSpeaker()
        opened = []
        ctx = Context(config=config, speaker=speaker, open_url=opened.append,
                      now=lambda: dt.datetime(2026, 10, 24, 14, 5))
        assistant = Assistant(config, ScriptedListener(lines), speaker, brain, ctx)
        assistant.opened = opened
        return assistant

    return build


def test_wake_word_stripping(make):
    a = make()
    assert a.strip_wake_word("Jarvis, what time is it") == "what time is it"
    assert a.strip_wake_word("hey jarvis") == ""
    assert a.strip_wake_word("what time is it") is None
    assert a.strip_wake_word("jarvisfoo") is None


def test_no_wake_word_mode(make):
    assert make(require_wake_word=False).strip_wake_word("what time is it") == "what time is it"


def test_time_and_date(make):
    a = make()
    assert a.respond("what time is it") == "It's 2:05 PM."
    assert a.respond("what's the date") == "Today is Saturday, October 24, 2026."
    assert a.respond("hello").startswith("Good afternoon")


@pytest.mark.parametrize("command,answer", [
    ("what is 2 plus 2", "That's 4."),
    ("calculate 10 divided by 4", "That's 2.5."),
    ("what's 3 times 7", "That's 21."),
    ("what is 5 squared", "That's 25."),
    ("what is 1 divided by 0", "Sorry, I couldn't work that out."),
])
def test_calculator(make, command, answer):
    assert make().respond(command) == answer


def test_safe_eval_rejects_code():
    assert to_expression("__import__('os')") is None
    with pytest.raises(ValueError):
        safe_eval("9 ** 9999")


def test_non_math_question_goes_to_brain(make):
    brain = FakeBrain()
    assert make(brain=brain).respond("what is the capital of France") == "brain answer"
    assert brain.questions == ["what is the capital of France"]


def test_open_and_search(make):
    a = make()
    assert a.respond("open youtube") == "Opening youtube."
    a.respond("search for python tutorials")
    assert a.opened == ["https://www.youtube.com", "https://www.google.com/search?q=python+tutorials"]


def test_notes_roundtrip(make):
    a = make()
    assert a.respond("read my notes") == "You don't have any notes yet."
    a.respond("take a note buy milk")
    assert a.respond("read my notes") == "Your latest notes: buy milk."


def test_timer_fires(make):
    a = make()
    assert a.respond("set a timer for 0.05 seconds") == "Timer set for 0.05 seconds."
    a.context.timers[-1].join(1)
    assert a.speaker.said[-1] == "Your 0.05 seconds timer is done."


def test_exit_raises(make):
    with pytest.raises(Exit):
        make().respond("goodbye")


def test_unknown_without_brain(make):
    assert "don't know" in make().respond("sing me a song")


def test_run_loop(make):
    a = make(["what time is it", "jarvis what time is it", "jarvis", "tell me a joke", "jarvis goodbye", "never heard"])
    a.run()
    said = a.speaker.said
    assert said[0].startswith("Jarvis online")
    assert said[1] == "It's 2:05 PM."  # first line ignored: no wake word
    assert said[2] == "Yes?"
    assert said[4].startswith("Goodbye")
    assert len(said) == 5


# --- YouTube videos ------------------------------------------------------------

import io
import json
import urllib.error
from types import SimpleNamespace

from jarvis import youtube
from jarvis.brain import Brain


def test_youtube_url_forms():
    want = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    for link in ["https://youtu.be/dQw4w9WgXcQ?si=abc", "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=5",
                 "youtube.com/watch?feature=share&v=dQw4w9WgXcQ", "https://m.youtube.com/shorts/dQw4w9WgXcQ",
                 "summarize this https://www.youtube.com/live/dQw4w9WgXcQ please"]:
        assert youtube.youtube_url(link) == want
    assert youtube.youtube_url("https://example.com/watch?v=dQw4w9WgXcQ") == ""
    assert youtube.youtube_url("https://youtu.be/short") == ""


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_ask_gemini_sends_link_and_key(monkeypatch):
    sent = {}

    def fake_urlopen(request, timeout):
        sent["url"], sent["key"], sent["body"] = request.full_url, request.get_header("X-goog-api-key"), json.loads(request.data)
        return FakeResponse(json.dumps({"candidates": [{"content": {"parts": [{"text": "A cat plays piano."}]}}]}).encode())

    monkeypatch.setattr(youtube.urllib.request, "urlopen", fake_urlopen)
    out = youtube.watch({"url": "https://youtu.be/dQw4w9WgXcQ", "question": "What happens?"}, "AQ.key", "gemini-flash-latest")
    assert out == youtube.UNTRUSTED_VIDEO + "A cat plays piano."
    assert sent["url"].endswith("/models/gemini-flash-latest:generateContent")
    assert sent["key"] == "AQ.key"
    assert sent["body"]["contents"][0]["parts"] == [
        {"file_data": {"file_uri": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}}, {"text": "What happens?"}]


def test_ask_gemini_bad_key(monkeypatch):
    def fake_urlopen(request, timeout):
        body = io.BytesIO(json.dumps({"error": {"message": "API key not valid."}}).encode())
        raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {}, body)

    monkeypatch.setattr(youtube.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(youtube.VideoError, match="key didn't work"):
        youtube.ask_gemini("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "q", "bad", "m")


class FakeMessages:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.replies.pop(0)


def make_brain_with(replies, gemini_api_key="AQ.key"):
    brain = Brain.__new__(Brain)
    brain._anthropic = None
    brain.model, brain.effort, brain.messages = "m", "low", []
    brain.gemini_api_key, brain.gemini_model = gemini_api_key, "gemini-flash-latest"
    brain.tools = [youtube.TOOL] if gemini_api_key else []
    brain.system = "s"
    brain.client = SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages(replies)))
    return brain


def test_brain_watches_video(monkeypatch):
    monkeypatch.setattr(youtube, "ask_gemini", lambda video, question, key, model: f"seen {video}")
    tool_use = SimpleNamespace(type="tool_use", id="t1", name="watch_youtube_video",
                               input={"url": "https://youtu.be/dQw4w9WgXcQ", "question": "Summarize"})
    brain = make_brain_with([
        SimpleNamespace(stop_reason="tool_use", content=[tool_use]),
        SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="It's a song.")]),
    ])
    assert brain.ask("summarize https://youtu.be/dQw4w9WgXcQ") == "It's a song."
    calls = brain.client.beta.messages.calls
    assert [t["name"] for t in calls[0]["tools"]] == ["watch_youtube_video"]
    result = brain.messages[2]["content"][0]  # user question, tool call, tool result, answer
    assert result["tool_use_id"] == "t1" and "seen https://www.youtube.com/watch?v=dQw4w9WgXcQ" in result["content"]
    assert result["content"].startswith(youtube.UNTRUSTED_VIDEO)


def test_brain_without_gemini_key_offers_no_tools():
    brain = make_brain_with([SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="hi")])], "")
    brain.ask("hello")
    assert "tools" not in brain.client.beta.messages.calls[0]


def test_youtube_link_skips_builtin_skills(make):
    brain = FakeBrain()
    a = make(brain=brain)
    assert a.respond("help me understand https://youtu.be/dQw4w9WgXcQ") == "brain answer"
    assert a.respond("what can you do") != "brain answer"
