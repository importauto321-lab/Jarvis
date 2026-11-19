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


def test_mapping_reads_loose_columns_and_dates(tmp_path):
    from boss import mapping
    f = tmp_path / "x.csv"
    f.write_text("Inv #,Customer Name,Balance Due,Due Date,Date Paid\n"
                 "1001,Ann,\"$1,250.00\",11/05/2026,\n1002,Bob,300,2026-11-01,11/10/26\n")
    rows = mapping.read("invoices", str(f))
    assert rows[0]["invoice"] == "1001" and rows[0]["amount"] == 1250.0 and rows[0]["due_date"] == "2026-11-05"
    assert rows[1]["paid_date"] == "2026-11-10"
    g = tmp_path / "bad.csv"
    g.write_text("foo,bar\n1,2\n")
    with pytest.raises(SystemExit):
        mapping.read("invoices", str(g))


def test_merge_json_marks_data_real(tmp_path, monkeypatch):
    from boss import mapping
    monkeypatch.setattr(mapping, "DATA", tmp_path)
    mapping.merge_json("team.json", {"sample": True, "loads": [1]})
    d = json.loads((tmp_path / "team.json").read_text())
    assert "sample" not in d and d["loads"] == [1]


def _settings(tmp_path, monkeypatch, **extra):
    from leads import drafts
    sp = tmp_path / "settings.json"
    sp.write_text(json.dumps({"team_emails": ["n@x.c", "k@x.c"], "owner_email": "me@x.c",
                              "owner_text_number": "555", **extra}))
    monkeypatch.setattr(drafts, "SETTINGS", sp)


def test_delivery_is_drafts_only(tmp_path, monkeypatch):
    from boss import deliver, briefing
    _settings(tmp_path, monkeypatch)
    monkeypatch.setattr(deliver, "OUT", tmp_path / "out")
    t = deliver.email_draft("team", "Team briefing", "hello", date(2026, 11, 19))
    assert "To: n@x.c, k@x.c" in t.read_text() and "NOT SENT" in t.read_text()
    txt = deliver.short_text(briefing.load_inputs(), date(2026, 11, 19))
    assert len(txt) <= 450 and "Briefing" in txt
    with pytest.raises(SystemExit):
        deliver.send_text("x")


def test_checker_needs_key_and_parses_reply(monkeypatch):
    from leads import checker
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        checker.second_opinion("hi")
    out = checker.second_opinion("hi", key="k", post=_fake_openai("VERDICT: agree"))
    assert out == "VERDICT: agree"


def _fake_openai(text):
    class R(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass
    payload = json.dumps({"choices": [{"message": {"content": text}}]}).encode()
    return lambda req, timeout=0: R(payload)


def test_doctor_reports_without_changing_anything(tmp_path, monkeypatch):
    from leads import doctor
    out = doctor.report()
    assert "Nothing was changed" in out and "[todo]" in out


def test_gemini_checker_default(monkeypatch):
    from leads import checker
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        checker.second_opinion_gemini("hi")
    fake = _fake('VERDICT: disagree')
    assert checker.second_opinion_gemini("hi", key="k", post=fake) == "VERDICT: disagree"
