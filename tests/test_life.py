import io
import json
from datetime import date

import pytest

from life import engine, library
from boss import team_briefing
from leads import store


@pytest.fixture(autouse=True)
def tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(library, "DATA", tmp_path)
    monkeypatch.setattr(store, "DATA", tmp_path)


def test_new_entries_are_pending_and_only_approved_are_searchable():
    r = library.add("book", "Never Split the Difference", "Chris Voss", ["Ask calibrated questions to negotiate price"], route_to="sales")
    assert r["status"] == "pending" and library.ask("negotiate price") == []
    library.set_status(r["id"], "approved")
    assert library.ask("how do I negotiate price")[0]["id"] == r["id"]
    assert library.for_agent("sales")[0]["id"] == r["id"] and library.for_agent("loads") == []
    library.set_status(r["id"], "rejected")
    assert library.ask("negotiate") == []


def test_duplicate_source_not_saved_twice():
    a = library.add("video", "t", "https://youtu.be/x", ["l"])
    assert library.add("video", "t2", "https://youtu.be/x", ["l2"])["id"] == a["id"]


def _fake(text):
    class R(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass
    payload = json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode()
    return lambda req, timeout=0: R(payload)


def test_video_engine_saves_pending_and_rejects_non_youtube():
    r = engine.learn_video("https://www.youtube.com/watch?v=abc", key="k", post=_fake(
        'Sure {"title":"Pricing 101","lessons":["Quote by lane, not by car"],"tags":["pricing"],"route_to":"loads"}'))
    assert r["status"] == "pending" and r["route_to"] == "loads"
    with pytest.raises(SystemExit):
        engine.learn_video("https://evil.test/x", key="k", post=_fake("{}"))
    with pytest.raises(SystemExit):
        engine.learn_video("https://youtu.be/abc", key="k", post=_fake("no json here"))


def test_team_briefing_sections_and_draft_only(tmp_path, monkeypatch):
    data = team_briefing.load()
    monkeypatch.setattr(team_briefing, "HERE", tmp_path)
    t = team_briefing.build(data, date(2026, 11, 19))
    for n in "1234":
        assert f"{n}. " in t
    assert "SAMPLE DATA" in t and "car damaged" in t and "Nothing is sent" in t
    assert team_briefing.save_draft(t, date(2026, 11, 19)).read_text().startswith("Subject:")
