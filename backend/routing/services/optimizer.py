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
    """Pick the fuel stops that minimise total fuel cost for the whole trip.

    The vehicle covers `total_miles` and burns `total_miles / mpg` gallons. We
    choose stops so that no leg exceeds the vehicle range and the total cost of
    that fuel is as low as possible. This is solved exactly with a dynamic
    program over the on-route stations rather than a greedy heuristic, so it
    never makes a needless stop at a pricier station.

    Returns (stops, total_cost). Each chosen stop is annotated with the gallons
    and cost of the leg its fuel powers. Raises ValueError if some stretch of
    the route has no station within range.
    """
    # Collapse stations that sit at effectively the same point, keeping the
    # cheapest, so the list stays clean.
    deduped = []
    for s in sorted(on_route, key=lambda r: r.mile):
        if deduped and abs(s.mile - deduped[-1].mile) < 0.5:
            if s.station.retail_price < deduped[-1].station.retail_price:
                deduped[-1] = s
            continue
        deduped.append(s)

    # A station sitting essentially at the destination is not a useful stop -
    # you have already arrived - so drop anything within half a mile of the end.
    deduped = [s for s in deduped if s.mile < total_miles - 0.5]

    # Trip fits in a single tank - no fuel stop needed.
    if total_miles <= vehicle_range:
        return [], 0.0

    n = len(deduped)
    if n == 0:
        raise ValueError("No fuel station available within range for this route.")

    miles = [s.mile for s in deduped]
    price = [s.station.retail_price for s in deduped]
    INF = float("inf")

    # dp[j] = min cost to have j as a stop, with fuel paid for from mile 0 to j.
    # The first stop's price also covers the initial stretch from the origin.
    dp = [INF] * n
    parent = [-1] * n
    for j in range(n):
        if miles[j] <= vehicle_range + 1e-9:
            dp[j] = price[j] * miles[j] / mpg

    for j in range(n):
        if dp[j] == INF:
            continue
        for l in range(j + 1, n):
            gap = miles[l] - miles[j]
            if gap > vehicle_range + 1e-9:
                break  # miles is sorted, so every later l is even farther
            cost = dp[j] + price[j] * gap / mpg
            if cost < dp[l]:
                dp[l] = cost
                parent[l] = j

    # Finish: from the last stop we must be able to coast to the destination.
    best, best_k = INF, -1
    for k in range(n):
        if dp[k] == INF:
            continue
        if total_miles - miles[k] <= vehicle_range + 1e-9:
            total = dp[k] + price[k] * (total_miles - miles[k]) / mpg
            if total < best:
                best, best_k = total, k

    if best_k == -1:
        raise ValueError(
            "No fuel station available within range for part of this route."
        )

    # Reconstruct the chosen stops in order.
    chosen = []
    k = best_k
    while k != -1:
        chosen.append(deduped[k])
        k = parent[k]
    chosen.reverse()

    # Attribute each leg of fuel to the stop that pays for it. The first stop
    # also covers the stretch from the origin to itself.
    for i, stop in enumerate(chosen):
        next_mile = chosen[i + 1].mile if i + 1 < len(chosen) else total_miles
        leg_miles = next_mile - stop.mile
        if i == 0:
            leg_miles += stop.mile
        gallons = leg_miles / mpg
        stop.gallons = round(gallons, 2)
        stop.cost = round(gallons * stop.station.retail_price, 2)

    return chosen, round(best, 2)
