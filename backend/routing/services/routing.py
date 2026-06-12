"""OpenRouteService client.

The whole point of this module is to talk to the external routing API as little
as possible: a single POST returns both the geocoded-to-driving route geometry
and the total distance, so one request per user lookup is enough.
"""

import time

import requests
from django.conf import settings

ORS_BASE = "https://api.openrouteservice.org"
_TIMEOUT = 20
_RETRIES = 2


class RoutingError(Exception):
    pass


def _request(method, url, **kwargs):
    """Call ORS with a small retry so a transient 5xx does not fail the request."""
    last = None
    for attempt in range(_RETRIES + 1):
        try:
            resp = requests.request(method, url, timeout=_TIMEOUT, **kwargs)
        except requests.RequestException as exc:
            last = exc
        else:
            if resp.status_code < 500:
                return resp
            last = RoutingError(f"ORS returned {resp.status_code}")
        if attempt < _RETRIES:
            time.sleep(0.6 * (attempt + 1))
    if isinstance(last, Exception):
        raise RoutingError(str(last))
    raise RoutingError("ORS request failed.")


def geocode(text):
    """Resolve a free-text US place to (lat, lon). One ORS call."""
    if not settings.ORS_API_KEY:
        raise RoutingError("ORS_API_KEY is not configured.")
    resp = _request(
        "GET",
        f"{ORS_BASE}/geocode/search",
        params={
            "api_key": settings.ORS_API_KEY,
            "text": text,
            "boundary.country": "US",
            "size": 1,
        },
    )
    if resp.status_code != 200:
        raise RoutingError(f"Geocoding failed ({resp.status_code}).")
    features = resp.json().get("features", [])
    if not features:
        raise RoutingError(f"Could not find a US location for '{text}'.")
    lon, lat = features[0]["geometry"]["coordinates"]
    label = features[0]["properties"].get("label", text)
    return lat, lon, label


def driving_route(start_lat, start_lon, finish_lat, finish_lon):
    """Return (points, total_miles) for the driving route. One ORS call.

    points is a list of (lat, lon) vertices along the route.
    """
    if not settings.ORS_API_KEY:
        raise RoutingError("ORS_API_KEY is not configured.")
    resp = _request(
        "POST",
        f"{ORS_BASE}/v2/directions/driving-hgv/geojson",
        headers={"Authorization": settings.ORS_API_KEY},
        json={"coordinates": [[start_lon, start_lat], [finish_lon, finish_lat]]},
    )
    if resp.status_code != 200:
        raise RoutingError(f"Routing failed ({resp.status_code}).")
    features = resp.json().get("features", [])
    if not features:
        raise RoutingError("No route found between the given locations.")
    feature = features[0]
    coords = feature["geometry"]["coordinates"]  # [lon, lat] pairs
    points = [(c[1], c[0]) for c in coords]
    meters = feature["properties"]["summary"]["distance"]
    total_miles = meters / 1609.344
    return points, total_miles
