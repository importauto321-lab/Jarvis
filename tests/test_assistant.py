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
