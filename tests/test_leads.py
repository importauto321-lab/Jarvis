import json
import pytest
from leads import store, ranking, drafts

SETTINGS = dict(business_name="Acme Haul", your_name="Sam", business_address="1 Main St, Austin, TX 78701",
                reply_email="sam@acme.test", phone="555-0100", one_line_pitch="We haul cars.", service_area="TX")


@pytest.fixture(autouse=True)
def tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path)
    monkeypatch.setattr(drafts, "DRAFTS", tmp_path / "drafts")
    sp = tmp_path / "settings.json"
    sp.write_text(json.dumps(SETTINGS))
    monkeypatch.setattr(drafts, "SETTINGS", sp)


def test_add_dedupes_and_ranks():
    a = store.add(dict(name="Big Brokers", kind="broker", city_state="Dallas, TX", email="a@b.c", ships_cars="yes"))
    assert store.add(dict(name="big brokers", kind="broker", city_state="dallas, tx"))["id"] == a["id"]
    store.add(dict(name="Small Lot", kind="dealer", city_state="Waco, TX"))
    rows = ranking.rank(store.load())
    assert rows[0]["name"] == "Big Brokers"


def test_draft_has_unsubscribe_and_address_and_status():
    store.add(dict(name="Big Brokers", kind="broker", city_state="Dallas, TX", email="a@b.c"))
    made = drafts.write_drafts()
    text = made[0].read_text()
    assert "unsubscribe" in text and "1 Main St, Austin" in text
    assert store.load()[0]["status"] == "drafted"


def test_placeholder_settings_refused(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({**SETTINGS, "business_address": "FILL IN"}))
    with pytest.raises(SystemExit):
        drafts.load_settings()


def test_no_sending_code():
    import pathlib
    src = "".join(p.read_text() for p in pathlib.Path(drafts.__file__).parent.glob("*.py"))
    assert "smtplib" not in src and "send_message" not in src


def _fake(text):
    import io, json as j
    class R(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass
    payload = j.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode()
    return lambda req, timeout=0: R(payload)


def test_find_makes_candidates_only_and_drops_no_and_bad_email():
    from leads import finder
    text = 'Here: [{"name":"A Auto Transport","city_state":"Dallas, TX","email":"bad","ships_cars":"yes","notes":"Runs trucks."},' \
           '{"name":"B Lot","ships_cars":"no"}]'
    added = finder.find("broker", "Texas", key="k", post=_fake(text))
    assert [a["name"] for a in added] == ["A Auto Transport"]
    assert added[0]["status"] == "candidate" and added[0]["email"] == ""
    assert drafts.write_drafts() == []  # candidates get no drafts until kept


def test_research_updates_lead():
    from leads import finder
    l = store.add(dict(name="X", kind="dealer", city_state="Y", status="candidate"))
    finder.research(l["id"], key="k", post=_fake('{"ships_cars":"yes","email":"x@y.z","notes":"Ships weekly."}'))
    r = store.load()[0]
    assert r["email"] == "x@y.z" and r["ships_cars"] == "yes"
