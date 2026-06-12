"""In-memory US city search for the autocomplete dropdown.

The bundled city dataset is loaded once on first use and queried locally, so
typing in the search box never touches an external API. Population (where known)
is used to rank well-known cities first, so "Dallas" surfaces Dallas, TX rather
than a smaller namesake.
"""

import csv
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CITIES_CSV = DATA_DIR / "us_cities.csv"
POP_CSV = DATA_DIR / "top_cities.csv"


def _load_population():
    pop = {}
    if not POP_CSV.exists():
        return pop
    with open(POP_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["City"].strip().upper(), r["State"].strip().upper())
            try:
                pop[key] = int(r["Population"])
            except (KeyError, ValueError):
                continue
    return pop


@lru_cache(maxsize=1)
def _load():
    rows = []
    if not CITIES_CSV.exists():
        return rows
    pop = _load_population()
    seen = set()
    with open(CITIES_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            city = r["CITY"].strip()
            state = r["STATE_CODE"].strip().upper()
            state_name = r["STATE_NAME"].strip().upper()
            key = (city.upper(), state)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "city": city,
                    "state": state,
                    "label": f"{city}, {state}",
                    "lat": float(r["LATITUDE"]),
                    "lon": float(r["LONGITUDE"]),
                    "pop": pop.get((city.upper(), state_name), 0),
                }
            )
    return rows


def search(query, limit=8):
    """Return up to `limit` cities: prefix matches (ranked by population, then
    name length) first, then substring matches."""
    q = (query or "").strip().lower()
    if len(q) < 2:
        return []
    rows = _load()
    starts, contains = [], []
    for row in rows:
        name = row["city"].lower()
        if name.startswith(q):
            starts.append(row)
        elif q in name or q in row["label"].lower():
            contains.append(row)

    starts.sort(key=lambda r: (-r["pop"], len(r["city"]), r["city"]))
    contains.sort(key=lambda r: (-r["pop"], len(r["city"]), r["city"]))
    result = (starts + contains)[:limit]
    return [{k: r[k] for k in ("city", "state", "label", "lat", "lon")} for r in result]
