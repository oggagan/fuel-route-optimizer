"""Pure geometry helpers - no external calls."""

import math

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in miles."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def cumulative_distances(points):
    """Given [(lat, lon), ...] return the running distance in miles at each vertex."""
    cum = [0.0]
    for i in range(1, len(points)):
        d = haversine_miles(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1])
        cum.append(cum[-1] + d)
    return cum


def point_to_segment_miles(plat, plon, alat, alon, blat, blon):
    """Approximate shortest distance (miles) from point P to segment A-B.

    Uses a local equirectangular projection, which is accurate enough at the
    few-mile scale we care about for the route corridor.
    """
    lat0 = math.radians((alat + blat) / 2)
    deg_to_mi_lat = 69.0
    deg_to_mi_lon = 69.0 * math.cos(lat0)

    ax, ay = alon * deg_to_mi_lon, alat * deg_to_mi_lat
    bx, by = blon * deg_to_mi_lon, blat * deg_to_mi_lat
    px, py = plon * deg_to_mi_lon, plat * deg_to_mi_lat

    dx, dy = bx - ax, by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0:
        t = 0.0
    else:
        t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
        t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy), t
