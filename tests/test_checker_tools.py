import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import openai_key  # noqa: E402
import review  # noqa: E402

FAKE = "sk-" + "x" * 40


class Keychain:
    def __init__(self):
        self.stored, self.argv = "", []

    def __call__(self, args, input=None, **kw):
        self.argv.append(args)
        if args[1] == "-i":
            self.stored = input.rsplit('-w "', 1)[1].split('"')[0]
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(args, 0 if self.stored else 44, self.stored + "\n", "")


def test_key_is_saved_without_appearing_on_a_command_line():
    chain = Keychain()
    openai_key.save_key(FAKE, run=chain)
    assert chain.stored == FAKE
    assert not any(FAKE in part for args in chain.argv for part in args)


@pytest.mark.parametrize("bad", ["", "hello", "sk-short", 'sk-' + 'x' * 30 + '" -A "', "sk-abc def" + "x" * 30])
def test_bad_keys_are_refused(bad):
    chain = Keychain()
    with pytest.raises(ValueError):
        openai_key.save_key(bad, run=chain)
    assert chain.stored == ""


def test_review_sends_only_the_diff_and_returns_the_answer():
    seen = {}

    def post(req, timeout=0):
        seen["body"] = json.loads(req.data)

        class R(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): pass
        return R(json.dumps({"choices": [{"message": {"content": "VERDICT: ship"}}]}).encode())

    assert review.review("+print(1)", "k", "m", post=post) == "VERDICT: ship"
    assert seen["body"]["messages"][1]["content"] == "+print(1)"


@pytest.mark.parametrize("secret", [FAKE, "ghp_" + "a" * 36, "API_SERVER_KEY=" + "0" * 48])
def test_nothing_is_sent_when_the_diff_holds_a_secret(secret):
    def post(*a, **k):
        raise AssertionError("must not send")
    with pytest.raises(review.ReviewError, match="Nothing was sent"):
        review.review("+x = '" + secret + "'", "k", "m", post=post)


def test_empty_diff_bad_key_and_model_choice(monkeypatch):
    with pytest.raises(review.ReviewError, match="no change"):
        review.review("  ", "k", "m")

    def refused(req, timeout=0):
        raise urllib.error.HTTPError("u", 401, "x", {}, None)
    with pytest.raises(review.ReviewError, match="refused"):
        review.review("+a", "k", "m", post=refused)
    monkeypatch.delenv("JARVIS_REVIEW_MODEL", raising=False)
    assert review.pick_model(["gpt-4o", "gpt-4.1"]) == "gpt-4.1"
    with pytest.raises(review.ReviewError):
        review.pick_model(["other"])
