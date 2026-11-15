"""Polygon validation and geometry for user-drawn fields (pure python; shapely is not a dependency)."""
from __future__ import annotations

import math

R_AUTH = 6371007.2          # authalic radius of WGS84 (m): spherical area formula with this radius is within ~0.1 % of the ellipsoid
MAX_VERTICES, MIN_HA, MAX_HA = 200, 0.5, 2000.0


class GeomError(ValueError):
    pass


def area_m2(ring) -> float:
    """Geodesic-equivalent area of a lon/lat ring (equal-area sphere with the WGS84 authalic radius)."""
    s = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        s += math.radians(x2 - x1) * (2 + math.sin(math.radians(y1)) + math.sin(math.radians(y2)))
    return abs(s) * R_AUTH ** 2 / 2


def _signed(ring) -> float:
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:])) / 2


def _local(ring):
    lat0 = sum(p[1] for p in ring) / len(ring)
    kx, ky = 111320 * math.cos(math.radians(lat0)), 110574
    return [(p[0] * kx, p[1] * ky) for p in ring]


def _orient(a, b, c):
    v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)


def _on(a, b, c):
    return min(a[0], b[0]) - 1e-9 <= c[0] <= max(a[0], b[0]) + 1e-9 and min(a[1], b[1]) - 1e-9 <= c[1] <= max(a[1], b[1]) + 1e-9


def _seg_hit(p1, p2, p3, p4) -> bool:
    o1, o2, o3, o4 = _orient(p1, p2, p3), _orient(p1, p2, p4), _orient(p3, p4, p1), _orient(p3, p4, p2)
    if o1 != o2 and o3 != o4:
        return True
    return (o1 == 0 and _on(p1, p2, p3)) or (o2 == 0 and _on(p1, p2, p4)) or (o3 == 0 and _on(p3, p4, p1)) or (o4 == 0 and _on(p3, p4, p2))


def self_intersects(ring) -> bool:
    """True if any two non-adjacent edges of the closed ring touch or cross (in metres on a local projection)."""
    pts = _local(ring)
    n = len(pts) - 1
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if _seg_hit(pts[i], pts[i + 1], pts[j], pts[j + 1]):
                return True
    return False


def validate(geometry) -> tuple[dict, float]:
    """(clean GeoJSON Polygon: closed, counter-clockwise, 6 decimals; area in ha) or raise GeomError with a plain reason."""
    if not isinstance(geometry, dict) or geometry.get("type") != "Polygon":
        t = geometry.get("type") if isinstance(geometry, dict) else type(geometry).__name__
        raise GeomError(f"geometry must be a single GeoJSON Polygon (got {t}); draw one shape at a time")
    rings = geometry.get("coordinates")
    if not isinstance(rings, list) or not rings or not isinstance(rings[0], list):
        raise GeomError("Polygon has no coordinates")
    if len(rings) != 1:
        raise GeomError("polygons with holes are not supported; draw the outer outline only")
    ring = []
    for p in rings[0]:
        if not isinstance(p, (list, tuple)) or len(p) < 2 or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in p[:2]):
            raise GeomError("every position must be [longitude, latitude] numbers")
        lon, lat = float(p[0]), float(p[1])
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise GeomError(f"position [{lon}, {lat}] is outside WGS84 longitude/latitude; send [lon, lat] in degrees")
        q = [round(lon, 6), round(lat, 6)]
        if not ring or q != ring[-1]:
            ring.append(q)
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring.pop()
    if len(ring) < 3:
        raise GeomError("a polygon needs at least 3 distinct corners")
    if len(ring) > MAX_VERTICES:
        raise GeomError(f"polygon has {len(ring)} vertices; the limit is {MAX_VERTICES}")
    ring.append(ring[0])
    if self_intersects(ring):
        raise GeomError("polygon crosses or touches itself; redraw it without crossing edges")
    ha = area_m2(ring) / 1e4
    if ha < MIN_HA:
        raise GeomError(f"area {ha:.2f} ha is under the {MIN_HA} ha minimum (about 1.2 acres)")
    if ha > MAX_HA:
        raise GeomError(f"area {ha:,.0f} ha is over the {MAX_HA:,.0f} ha maximum (about 4,900 acres)")
    if _signed(ring) < 0:
        ring.reverse()
    return {"type": "Polygon", "coordinates": [ring]}, ha


def in_ring(lon, lat, ring) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def centroid(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        f = x1 * y2 - x2 * y1
        a += f; cx += (x1 + x2) * f; cy += (y1 + y2) * f
    if abs(a) < 1e-18:
        return sum(p[0] for p in ring[:-1]) / (len(ring) - 1), sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
    return cx / (3 * a), cy / (3 * a)


def sample_grid(ring, max_pts=25):
    """Evenly spaced points inside the ring: the finest bbox grid that yields at most max_pts, at least 1 point.
    Returns (points [[lon, lat]], interior point nearest the centroid)."""
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    best = []
    for n in range(2, 16):
        pts = [[min(xs) + (i + .5) * (max(xs) - min(xs)) / n, min(ys) + (j + .5) * (max(ys) - min(ys)) / n]
               for i in range(n) for j in range(n)]
        pts = [p for p in pts if in_ring(p[0], p[1], ring)]
        if len(pts) > max_pts:
            break
        if len(pts) >= len(best):
            best = pts
    cx, cy = centroid(ring)
    if in_ring(cx, cy, ring):
        inner = [cx, cy]
        if len(best) < max_pts:
            best = [inner] + best
    else:
        inner = min(best, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2) if best else [ring[0][0], ring[0][1]]
    if not best:
        best = [inner]
    return [[round(p[0], 6), round(p[1], 6)] for p in best], [round(inner[0], 6), round(inner[1], 6)]
