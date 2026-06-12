"""Fuel-stop optimisation.

All of this runs locally on the route geometry returned by the single external
routing call - no further network access. The two jobs are:

  1. find which stations actually lie on the route (within a few miles), and at
     what mileage along the route they sit;
  2. pick a cost-effective set of fuel stops that respects the vehicle range,
     and add up what the fuel costs.

Assumptions (documented in the README):
  - the vehicle starts on a full tank (so the first `range` miles are already
    covered) and refuels along the way;
  - fuel burned between two consecutive fills is bought at the earlier fill's
    price, so total cost is the money actually spent at the chosen stations.
"""

from dataclasses import dataclass

from .geo import cumulative_distances, haversine_miles


@dataclass
class OnRouteStation:
    station: object
    mile: float          # distance along the route where the station sits
    detour: float        # how far off the route it is, in miles


def _build_vertex_grid(points, cell_deg):
    grid = {}
    for idx, (lat, lon) in enumerate(points):
        key = (int(lat / cell_deg), int(lon / cell_deg))
        grid.setdefault(key, []).append(idx)
    return grid


def find_on_route_stations(points, stations, corridor_miles):
    """Return stations within `corridor_miles` of the route, with their mileage.

    Uses a coarse spatial grid over the route vertices so each station only
    compares against nearby vertices instead of the whole polyline.
    """
    if not points:
        return []

    cum = cumulative_distances(points)
    cell_deg = max(corridor_miles / 69.0, 0.05)
    grid = _build_vertex_grid(points, cell_deg)

    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    pad = corridor_miles / 69.0
    min_lat, max_lat = min(lats) - pad, max(lats) + pad
    min_lon, max_lon = min(lons) - pad, max(lons) + pad

    results = []
    for st in stations:
        if st.latitude is None or st.longitude is None:
            continue
        if not (min_lat <= st.latitude <= max_lat and min_lon <= st.longitude <= max_lon):
            continue

        clat, clon = int(st.latitude / cell_deg), int(st.longitude / cell_deg)
        best_d = None
        best_idx = None
        for dlat in (-1, 0, 1):
            for dlon in (-1, 0, 1):
                for idx in grid.get((clat + dlat, clon + dlon), ()):
                    d = haversine_miles(st.latitude, st.longitude, points[idx][0], points[idx][1])
                    if best_d is None or d < best_d:
                        best_d, best_idx = d, idx
        if best_d is not None and best_d <= corridor_miles:
            results.append(OnRouteStation(station=st, mile=cum[best_idx], detour=best_d))

    results.sort(key=lambda r: r.mile)
    return results


def choose_fuel_stops(on_route, total_miles, vehicle_range, mpg):
    """Greedy cheapest-reachable selection respecting the vehicle range.

    Returns (stops, total_cost). `stops` is the ordered list of chosen
    OnRouteStation objects, each annotated with gallons and cost for the leg it
    powers. Raises ValueError if a gap longer than the range has no station.
    """
    # Collapse stations that sit at effectively the same point, keeping the
    # cheapest, so the list stays clean.
    deduped = []
    for s in on_route:
        if deduped and abs(s.mile - deduped[-1].mile) < 0.5:
            if s.station.retail_price < deduped[-1].station.retail_price:
                deduped[-1] = s
            continue
        deduped.append(s)

    stops = []
    position = 0.0
    remaining = vehicle_range  # miles of range left in the tank (starts full)

    while position + remaining < total_miles - 1e-6:
        window = [s for s in deduped if position < s.mile <= position + remaining + 1e-6]
        if not window:
            raise ValueError(
                "No fuel station available within range for part of this route."
            )
        # cheapest fuel; on a tie, go farther to make progress
        stop = min(window, key=lambda s: (s.station.retail_price, -s.mile))
        remaining -= stop.mile - position
        position = stop.mile
        remaining = vehicle_range  # fill to full
        stops.append(stop)

    # Attribute each leg of the trip to the fill that powers it and sum the cost.
    total_cost = 0.0
    for i, stop in enumerate(stops):
        next_mile = stops[i + 1].mile if i + 1 < len(stops) else total_miles
        leg_miles = next_mile - stop.mile
        gallons = leg_miles / mpg
        cost = gallons * stop.station.retail_price
        stop.gallons = round(gallons, 2)
        stop.cost = round(cost, 2)
        total_cost += cost

    return stops, round(total_cost, 2)
