"""Quote helper: miles x your rate per mile (plus minimum). The quote is a suggestion for you to send."""
import json
import urllib.parse
import urllib.request

from . import drafts

UA = {"User-Agent": "car-hauling-quote-helper"}


def quote(miles: float, car: str, s: dict) -> dict:
    rate, minimum = float(s["rate_per_mile"]), float(s.get("minimum_charge") or 0)
    price = max(round(miles * rate, 2), minimum)
    return {"car": car, "miles": round(miles, 1), "rate": rate, "price": price,
            "text": f"{car}: about {miles:,.0f} miles x ${rate:.2f}/mile = ${price:,.2f}"
                    + (" (minimum charge applied)" if price == minimum and miles * rate < minimum else "")}


def _get(url, opener=None):
    with (opener or urllib.request.urlopen)(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def road_miles(pickup: str, dropoff: str, opener=None) -> float:
    """Free lookup (OpenStreetMap + OSRM). Only called with --live. Check the result against your own sense."""
    pts = []
    for place in (pickup, dropoff):
        g = _get("https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + urllib.parse.quote(place), opener)
        if not g:
            raise SystemExit(f"Could not find '{place}'. Try 'City, ST' or give --miles.")
        pts.append(f"{g[0]['lon']},{g[0]['lat']}")
    r = _get(f"https://router.project-osrm.org/route/v1/driving/{pts[0]};{pts[1]}?overview=false", opener)
    return r["routes"][0]["distance"] / 1609.344
