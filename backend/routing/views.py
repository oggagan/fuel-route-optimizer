from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import FuelStation
from .services.cities import search as search_cities
from .services.optimizer import choose_fuel_stops, find_on_route_stations
from .services.routing import RoutingError, driving_route, geocode


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "stations": FuelStation.objects.count()})


@api_view(["GET"])
def cities(request):
    """Autocomplete suggestions for the location inputs."""
    return Response({"results": search_cities(request.GET.get("q", ""))})


def _resolve_endpoint(label, lat, lon, query):
    """Use client-supplied coordinates when present, else geocode the text."""
    if lat is not None and lon is not None:
        return float(lat), float(lon), (label or query)
    return geocode(query)


@api_view(["POST"])
def route(request):
    """Plan a fuel-optimised route.

    Body: {"start": "Dallas, TX", "finish": "Chicago, IL"}
    """
    data = request.data or {}
    start = (data.get("start") or "").strip()
    finish = (data.get("finish") or "").strip()
    if not start or not finish:
        return Response(
            {"error": "Both 'start' and 'finish' are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # When the client picks from the autocomplete it sends coordinates, so
        # we can skip geocoding and make only a single routing call.
        s_lat, s_lon, s_label = _resolve_endpoint(
            data.get("start_label"), data.get("start_lat"), data.get("start_lon"), start
        )
        f_lat, f_lon, f_label = _resolve_endpoint(
            data.get("finish_label"), data.get("finish_lat"), data.get("finish_lon"), finish
        )
        points, total_miles = driving_route(s_lat, s_lon, f_lat, f_lon)
    except RoutingError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    stations = list(
        FuelStation.objects.exclude(latitude__isnull=True).only(
            "opis_id", "name", "address", "city", "state", "retail_price",
            "latitude", "longitude",
        )
    )

    # Stations are geocoded to their city centre, so a stop on the highway can
    # sit a little off the route line. Start with a tight corridor and widen it
    # if a stretch has no reachable station, rather than failing outright.
    base = settings.STATION_CORRIDOR_MILES
    stops, total_cost, last_error = None, None, None
    for corridor in (base, base * 3, base * 6, base * 12):
        on_route = find_on_route_stations(points, stations, corridor)
        try:
            stops, total_cost = choose_fuel_stops(
                on_route, total_miles, settings.VEHICLE_RANGE_MILES, settings.VEHICLE_MPG
            )
            break
        except ValueError as exc:
            last_error = exc
    if stops is None:
        return Response({"error": str(last_error)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    return Response(
        {
            "start": {"query": start, "label": s_label, "lat": s_lat, "lon": s_lon},
            "finish": {"query": finish, "label": f_label, "lat": f_lat, "lon": f_lon},
            "total_distance_miles": round(total_miles, 1),
            "vehicle_range_miles": settings.VEHICLE_RANGE_MILES,
            "vehicle_mpg": settings.VEHICLE_MPG,
            "total_gallons": round(total_miles / settings.VEHICLE_MPG, 1),
            "total_fuel_cost": total_cost,
            "fuel_stops": [
                {
                    "name": s.station.name,
                    "address": s.station.address,
                    "city": s.station.city,
                    "state": s.station.state,
                    "price_per_gallon": round(s.station.retail_price, 3),
                    "lat": s.station.latitude,
                    "lon": s.station.longitude,
                    "mile_marker": round(s.mile, 1),
                    "gallons": getattr(s, "gallons", 0),
                    "leg_cost": getattr(s, "cost", 0),
                }
                for s in stops
            ],
            "route": [[lat, lon] for lat, lon in points],
        }
    )
