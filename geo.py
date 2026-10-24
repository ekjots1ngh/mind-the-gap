"""Where an address is, and its nearest tube station.

Postcodes are looked up on postcodes.io (free, no key). If the venue wifi
drops, or a test postcode isn't a real one, we fall back to the outcode
(e.g. "E8") and then to an approximate point for each street we use.
Station data: tfl_stations.json, (c) OpenStreetMap contributors (ODbL),
prepared by Oliver O'Brien (github.com/oobrien/vis).
"""
import json
import math
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})\b", re.I)

# Approximate centre of each street in our test sets: used only when the lookup fails.
APPROX = {
    "E14 5RE": (51.5047, -0.0144, "Tower Hamlets"), "E8 1HE": (51.5450, -0.0553, "Hackney"),
    "E1 6QL": (51.5215, -0.0717, "Tower Hamlets"), "SW9 8LH": (51.4622, -0.1130, "Lambeth"),
    "N1 0NY": (51.5340, -0.1040, "Islington"), "NW6 6JP": (51.5440, -0.1960, "Camden"),
    "W12 8LJ": (51.5045, -0.2250, "Hammersmith and Fulham"), "SE17 1JE": (51.4900, -0.0960, "Southwark"),
    "EC1V 0HB": (51.5276, -0.1025, "Islington"), "HA1 2RT": (51.5820, -0.3350, "Harrow"),
    "SW9 8JX": (51.4615, -0.1140, "Lambeth"), "W11 1LJ": (51.5150, -0.2050, "Kensington and Chelsea"),
    "E8 4AA": (51.5460, -0.0750, "Hackney"), "SE22 8HN": (51.4560, -0.0750, "Southwark"),
    "N7 6PA": (51.5540, -0.1130, "Islington"),
}

_cache = {}
_stations = None


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mind-the-gap-hackathon-demo"})
    with urllib.request.urlopen(req, timeout=4) as r:
        return json.loads(r.read().decode())


def normalise(text):
    m = POSTCODE_RE.search(text or "")
    return f"{m.group(1).upper()} {m.group(2).upper()}" if m else None


def locate(text):
    """Return {postcode, lat, lon, district, ward, source} or None."""
    pc = normalise(text)
    if not pc:
        return None
    if pc in _cache:
        return _cache[pc]
    out = None
    try:
        r = _get(f"https://api.postcodes.io/postcodes/{pc.replace(' ', '')}")["result"]
        out = {"postcode": r["postcode"], "lat": r["latitude"], "lon": r["longitude"],
               "district": r.get("admin_district"), "ward": r.get("admin_ward"), "source": "postcode"}
    except Exception:
        try:
            r = _get(f"https://api.postcodes.io/outcodes/{pc.split()[0]}")["result"]
            district = (r.get("admin_district") or [None])[0]
            out = {"postcode": pc, "lat": r["latitude"], "lon": r["longitude"],
                   "district": district, "ward": None, "source": "outcode"}
        except Exception:
            if pc in APPROX:
                lat, lon, district = APPROX[pc]
                out = {"postcode": pc, "lat": lat, "lon": lon, "district": district, "ward": None,
                       "source": "approximate"}
    if out:
        st = nearest_station(out["lat"], out["lon"])
        if st:
            out["station"] = st
        _cache[pc] = out
    return out


def _haversine(lat1, lon1, lat2, lon2):
    to = math.radians
    a = math.sin(to(lat2 - lat1) / 2) ** 2 + math.cos(to(lat1)) * math.cos(to(lat2)) * math.sin(to(lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(a))


def nearest_station(lat, lon):
    global _stations
    if _stations is None:
        path = ROOT / "static" / "data" / "tfl_stations.json"
        _stations = json.loads(path.read_text(encoding="utf-8"))["features"] if path.exists() else []
    best = None
    for f in _stations:
        slon, slat = f["geometry"]["coordinates"]
        d = _haversine(lat, lon, slat, slon)
        if best is None or d < best["metres"]:
            lines = [x["name"] for x in f["properties"].get("lines", []) if "Thameslink" not in x["name"] and "Crossrail 2" not in x["name"]]
            best = {"name": f["properties"]["name"], "lat": slat, "lon": slon, "metres": round(d), "lines": lines}
    if best:
        best["walk_min"] = max(1, round(best["metres"] / 80))
    return best
