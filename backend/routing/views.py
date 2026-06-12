from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import FuelStation
from .services.optimizer import choose_fuel_stops, find_on_route_stations
from .services.routing import RoutingError, driving_route, geocode


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "stations": FuelStation.objects.count()})


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
        # Resolve endpoints, then one routing call for the whole geometry.
        s_lat, s_lon, s_label = geocode(start)
        f_lat, f_lon, f_label = geocode(finish)
        points, total_miles = driving_route(s_lat, s_lon, f_lat, f_lon)
    except RoutingError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    stations = list(
        FuelStation.objects.exclude(latitude__isnull=True).only(
            "opis_id", "name", "address", "city", "state", "retail_price",
            "latitude", "longitude",
        )
    )
    on_route = find_on_route_stations(points, stations, settings.STATION_CORRIDOR_MILES)

    try:
        stops, total_cost = choose_fuel_stops(
            on_route, total_miles, settings.VEHICLE_RANGE_MILES, settings.VEHICLE_MPG
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

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
