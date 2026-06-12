# Fuel Route Optimizer

An API that plans a driving route between two US locations and picks
cost-effective fuel stops along the way, given a vehicle with a 500-mile range
that does 10 miles per gallon. It returns the route geometry, the chosen fuel
stops, and the total money spent on fuel.

Backend is Django + Django REST Framework; frontend is a React + Vite single
page app with a Leaflet map.

## How it works

1. The two endpoints are geocoded and a single routing call to
   [OpenRouteService](https://openrouteservice.org/) returns the full driving
   geometry and total distance.
2. The ~8,000 fuel stations from the supplied price list are geocoded **once at
   import time**, offline, by joining on city + state against a bundled US
   cities dataset (no per-request geocoding). The result is cached in the DB.
3. Stations that fall within a few miles of the route are located using a
   spatial grid over the route vertices, and projected onto the route to get
   their mileage.
4. A dynamic program over the on-route stations selects the set of stops that
   minimises the total fuel cost while never exceeding the vehicle range. This
   is exact rather than a greedy heuristic, so it never makes a needless stop at
   a pricier station. If a stretch of the route has no station within a tight
   corridor, the corridor is widened before giving up.

### External API usage

The route endpoint makes **three** OpenRouteService calls per request: one to
geocode each endpoint and one for the route itself. All fuel-stop logic runs
locally on the returned geometry, so no further calls are needed regardless of
how many stops a route has.

### Assumptions

- The vehicle starts on a full tank, so the first 500 miles are already covered
  and the truck refuels as it goes.
- Fuel burned between two consecutive fills is bought at the earlier fill's
  price, so the reported total is the money actually spent at the chosen stops.
  A trip under 500 miles therefore needs no purchase and reports `$0`.
- Station coordinates come from a city-level dataset, so a stop is placed at the
  centre of its city. This is accurate enough to decide which stations lie along
  a long-haul route.
- The supplied price list is concentrated in the Midwest and East. A few western
  corridors (for example San Francisco to Las Vegas) have no listed station
  within range, and the API returns a clear message rather than a wrong answer.

## API

### `GET /api/health`
Returns service status and the number of loaded stations.

### `POST /api/route`
Request:
```json
{ "start": "Dallas, TX", "finish": "Chicago, IL" }
```
Response (trimmed):
```json
{
  "total_distance_miles": 969.7,
  "total_gallons": 97.0,
  "total_fuel_cost": 266.35,
  "fuel_stops": [
    {
      "name": "EXTRA MILE TRUCK STOP",
      "city": "Hooks", "state": "TX",
      "price_per_gallon": 2.817,
      "lat": 33.45, "lon": -94.35,
      "mile_marker": 166.3,
      "gallons": 0.9, "leg_cost": 2.6
    }
  ],
  "route": [[32.78, -96.79], "..."]
}
```

## Local setup

### Backend
```bash
cd backend
python -m venv venv
source venv/Scripts/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # then add your ORS_API_KEY
python manage.py migrate
python manage.py import_stations ../fuel-prices-for-be-assessment.csv
python manage.py runserver
```

Add `--ors-fallback` to `import_stations` to resolve the small number of cities
the offline dataset misses via OpenRouteService.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
The dev server runs on http://localhost:5173 and proxies `/api` to Django.

## Tech

- Django 6 + Django REST Framework
- PostgreSQL in production, SQLite for local dev
- OpenRouteService for geocoding and routing
- React + Vite + Leaflet (OpenStreetMap tiles)
