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


FULL = {**SETTINGS, "rate_per_mile": "0.85", "minimum_charge": "300", "reminder_days_late": "7",
        "demand_days_late": "30", "payment_deadline_days": "10", "google_review_link": "https://g.page/r/x",
        "attorney_name": "Pat"}


def _inv(tmp_path, monkeypatch, rows):
    from leads import invoices
    sp = tmp_path / "settings.json"; sp.write_text(json.dumps(FULL))
    monkeypatch.setattr(drafts, "SETTINGS", sp)
    f = tmp_path / "in.csv"
    f.write_text("invoice,customer,email,load,amount,due_date,paid_date\n" + "\n".join(rows))
    invoices.import_csv(str(f))
    return invoices


def test_quote_math_and_minimum():
    from leads import quotes
    assert quotes.quote(1000, "Civic", FULL)["price"] == 850.0
    assert quotes.quote(100, "Civic", FULL)["price"] == 300.0


def test_chase_demand_review(tmp_path, monkeypatch):
    from datetime import date
    inv = _inv(tmp_path, monkeypatch, [
        "1,Ann,a@x.c,L1,500,2026-10-01,",      # 40 days late
        "2,Bob,b@x.c,L2,400,2026-11-01,",      # 9 days late
        "3,Cy,c@x.c,L3,300,2026-10-01,2026-10-05"])  # paid
    t = date(2026, 11, 10)
    chase = inv.run("chase", t)           # Ann (40) and Bob (9) both past 7 days
    assert len(chase) == 2
    assert inv.run("chase", t) == []      # never drafted twice
    dem = inv.run("demand", t)            # Ann only
    assert len(dem) == 1
    txt = dem[0].read_text()
    assert "NOT YET APPROVED BY Pat" in txt and "L1" in txt and "$500.00" in txt and "November 20, 2026" in txt
    rev = inv.run("review", t)            # Cy only
    assert len(rev) == 1 and "g.page" in rev[0].read_text()


def test_no_sending_code_in_invoices():
    import pathlib
    src = "".join(p.read_text() for p in pathlib.Path(drafts.__file__).parent.glob("*.py"))
    assert "smtplib" not in src and "sendmail" not in src


def test_inbox_sorts_urgent_first_and_flags_junk(tmp_path):
    from leads import inbox
    store.add(dict(name="Big", kind="broker", city_state="X", email="ann@big.com"))
    msgs = [
        {"from": "news@shop.com", "subject": "50% off sale ends", "body": "unsubscribe here", "date": ""},
        {"from": "ann@big.com", "subject": "URGENT: car damaged at delivery", "body": "claim", "date": ""},
        {"from": "bob@x.com", "subject": "Quote for a Civic?", "body": "how much", "date": ""},
    ]
    out = inbox.sort_messages(msgs, owners={"Nicole": ["claim"]})
    assert out[0]["tier"] == "URGENT" and out[0]["owner"] == "Nicole"
    assert out[-1]["tier"] == "JUNK?"
    assert "nothing was moved" in inbox.report(out)


def test_inbox_reads_json_file(tmp_path):
    from leads import inbox
    f = tmp_path / "m.json"
    f.write_text(json.dumps([{"from": "a@b.c", "subject": "hi", "body": "", "date": ""}]))
    assert len(inbox.load_messages(str(f))) == 1


def test_load_match_and_truck(tmp_path):
    from leads import loads
    L = [
        dict(id="1", source="SD", pickup="Dallas, TX", dropoff="Miami, FL", miles="1300", price="1300", vehicle="Civic", pickup_date="2026-11-12"),
        dict(id="2", source="CD", pickup="Orlando, FL", dropoff="Houston, TX", miles="1000", price="600", vehicle="F150", pickup_date="2026-11-13"),
        dict(id="3", source="SD", pickup="Seattle, WA", dropoff="Boise, ID", miles="500", price="900", vehicle="Mini", pickup_date="2026-11-12"),
        dict(id="4", source="SD", pickup="Austin, TX", dropoff="Tampa, FL", miles="1200", price="1500", vehicle="Tesla", pickup_date="2026-11-30"),
    ]
    found = loads.match(L, [{"from": "TX", "to": "FL"}], min_per_mile=0.7)
    assert [l["id"] for l in found] == ["4", "1"]  # 2 is below $0.70/mi (0.60); 3 off route
    plan = loads.build_truck(found, capacity=9, window_days=5)
    assert [l["id"] for l in plan] == ["4"]  # 1 is 18 days from the best load
    assert "No loads" in loads.summary([])


def test_boards_off_by_default():
    from leads import boards
    with pytest.raises(SystemExit):
        boards.search("Super Dispatch", [])
