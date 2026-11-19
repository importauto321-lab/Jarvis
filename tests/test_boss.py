from datetime import date

import pytest

from boss import briefing
from leads import store


@pytest.fixture(autouse=True)
def tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path)


def test_sample_briefing_has_six_parts_and_stays_short():
    text = briefing.build(briefing.load_inputs(), date(2026, 11, 19))
    for n in "123456":
        assert f"{n}. " in text
    assert "SAMPLE DATA" in text and len(text.split()) <= 500
    assert "car damaged" in text            # urgent email shown
    assert "50% off" not in text            # junk left out
    assert "Not connected yet" in text      # no revenue source yet


def test_real_revenue_and_draft_counts(tmp_path):
    (tmp_path / "invoice_drafts" / "demand").mkdir(parents=True)
    (tmp_path / "invoice_drafts" / "demand" / "1.txt").write_text("x")
    text = briefing.build({"revenue_yesterday": 1234.5}, date(2026, 11, 19))
    assert "$1,234.50" in text and "1 demand letters (attorney must approve)" in text
    assert "SAMPLE" not in text


def test_save_writes_file_only(tmp_path, monkeypatch):
    monkeypatch.setattr(briefing, "HERE", tmp_path)
    p = briefing.save("hello", date(2026, 11, 19))
    assert p.read_text() == "hello"


def test_no_sending_code():
    import pathlib
    src = "".join(p.read_text() for p in pathlib.Path(briefing.__file__).parent.glob("*.py"))
    assert "smtplib" not in src and "send_message" not in src


def test_evening_and_weekly_are_blunt_and_use_goals():
    from boss import review
    data = review.load()
    t = date(2026, 11, 19)
    ev = review.evening(data, t)
    assert "SAMPLE DATA" in ev and "BEHIND" in ev and "Biggest leak: 'no reply to quote'" in ev
    wk = review.weekly(data, t)
    assert "What to fix" in wk and "No money collected on: 2026-11-17" in wk
    assert "No activity logged" in review.evening(data, date(2026, 11, 22))


def test_no_goal_is_not_invented():
    from boss import review
    ev = review.evening({"days": [], "goals": {}}, date(2026, 11, 19))
    assert "no goal set" in ev


def test_chaser_status_steps(tmp_path):
    import json
    from leads import drafts, invoices
    f = tmp_path / "in.csv"
    f.write_text("invoice,customer,email,load,amount,due_date,paid_date\n"
                 "1,Ann,a@x.c,L1,500,2026-10-01,\n2,Bob,b@x.c,L2,400,2026-11-14,\n3,Cy,c@x.c,L3,300,2026-11-01,\n")
    invoices.import_csv(str(f))
    rows = invoices.chaser_status(date(2026, 11, 19))
    assert [(r["invoice"], r["step"].split(":")[0]) for r in rows] == [
        ("1", "Demand letter due"), ("3", "Reminder due"), ("2", "Wait")]


def test_dashboard_is_one_safe_page(tmp_path):
    from boss import dashboard, review
    inputs = briefing.load_inputs()
    inputs["calendar"][0]["title"] = "<script>alert(1)</script>"
    html = dashboard.render(inputs, review.load(), date(2026, 11, 19))
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "Evening summary" in html and "Invoice chaser" in html and "http" not in html.replace("viewport", "")
