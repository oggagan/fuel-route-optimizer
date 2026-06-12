"""Load the fuel-price CSV into the database, geocoding each station once.

Geocoding is done offline by joining on (city, state) against a bundled US
cities dataset, so importing 8000+ rows needs zero network calls. Any city the
offline dataset misses can optionally be resolved through OpenRouteService with
--ors-fallback (those results are cached in the DB just like the rest).
"""

import csv
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from routing.models import FuelStation

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
CITIES_CSV = DATA_DIR / "us_cities.csv"


def load_city_index():
    if not CITIES_CSV.exists():
        raise CommandError(f"City dataset not found at {CITIES_CSV}")
    index = {}
    with open(CITIES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["CITY"].strip().upper(), row["STATE_CODE"].strip().upper())
            index[key] = (float(row["LATITUDE"]), float(row["LONGITUDE"]))
    return index


class Command(BaseCommand):
    help = "Import fuel stations from the assessment CSV with offline geocoding."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to the fuel-prices CSV")
        parser.add_argument(
            "--ors-fallback",
            action="store_true",
            help="Resolve cities missing from the offline dataset via OpenRouteService.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        cities = load_city_index()
        self.stdout.write(f"Loaded {len(cities)} cities for offline geocoding.")

        stations = []
        missing = {}  # (city, state) -> placeholder list of station dicts
        with open(csv_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                city = row["City"].strip()
                state = row["State"].strip().upper()
                key = (city.upper(), state)
                coords = cities.get(key)
                rack = row["Rack ID"].strip()
                rec = {
                    "opis_id": int(row["OPIS Truckstop ID"]),
                    "name": row["Truckstop Name"].strip(),
                    "address": row["Address"].strip(),
                    "city": city,
                    "state": state,
                    "rack_id": int(rack) if rack else None,
                    "retail_price": float(row["Retail Price"]),
                    "latitude": coords[0] if coords else None,
                    "longitude": coords[1] if coords else None,
                }
                stations.append(rec)
                if coords is None:
                    missing.setdefault(key, []).append(rec)

        geocoded = sum(1 for s in stations if s["latitude"] is not None)
        self.stdout.write(
            f"Parsed {len(stations)} stations - {geocoded} geocoded offline, "
            f"{len(missing)} unique cities unresolved."
        )

        if missing and options["ors_fallback"]:
            self._ors_fallback(missing)
            geocoded = sum(1 for s in stations if s["latitude"] is not None)
            self.stdout.write(f"After ORS fallback: {geocoded} geocoded.")

        with transaction.atomic():
            FuelStation.objects.all().delete()
            FuelStation.objects.bulk_create(
                [FuelStation(**s) for s in stations], batch_size=1000
            )

        self.stdout.write(self.style.SUCCESS(f"Imported {len(stations)} stations."))

    def _ors_fallback(self, missing):
        from routing.services.routing import RoutingError, geocode

        self.stdout.write(f"Resolving {len(missing)} cities via OpenRouteService...")
        for (city_u, state), recs in missing.items():
            try:
                lat, lon, _ = geocode(f"{recs[0]['city']}, {state}, USA")
            except RoutingError as exc:
                self.stderr.write(f"  skip {city_u}, {state}: {exc}")
                continue
            for rec in recs:
                rec["latitude"] = lat
                rec["longitude"] = lon
            time.sleep(0.6)  # stay well under the free rate limit
