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
