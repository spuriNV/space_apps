"""Polygon validation and geometry for user-drawn fields (pure python; shapely is not a dependency)."""
from __future__ import annotations

import math

R_AUTH = 6371007.2          # authalic radius of WGS84 (m): spherical area formula with this radius is within ~0.1 % of the ellipsoid
MAX_VERTICES, MIN_HA, MAX_HA = 400, 0.5, 2000.0
MAX_PARTS, MAX_HOLES = 20, 20


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


def _clean_ring(raw, what) -> list:
    """Closed ring of 6-decimal [lon, lat] from raw GeoJSON positions (consecutive duplicates dropped)."""
    if not isinstance(raw, list):
        raise GeomError(f"{what} has no coordinates")
    ring = []
    for p in raw:
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
        raise GeomError(f"{what} needs at least 3 distinct corners")
    ring.append(ring[0])
    return ring


def polys(geometry) -> list:
    """List of polygons (each [shell, hole, ...]) of a Polygon or MultiPolygon geometry."""
    return [geometry["coordinates"]] if geometry["type"] == "Polygon" else list(geometry["coordinates"])


def to_geometry(parts) -> dict:
    return {"type": "Polygon", "coordinates": parts[0]} if len(parts) == 1 else {"type": "MultiPolygon", "coordinates": parts}


def part_ha(part) -> float:
    return (area_m2(part[0]) - sum(area_m2(h) for h in part[1:])) / 1e4


def in_part(lon, lat, part) -> bool:
    return in_ring(lon, lat, part[0]) and not any(in_ring(lon, lat, h) for h in part[1:])


def _edges_hit(pa, pb) -> bool:
    for i in range(len(pa) - 1):
        for j in range(len(pb) - 1):
            if _seg_hit(pa[i], pa[i + 1], pb[j], pb[j + 1]):
                return True
    return False


def validate(geometry) -> tuple[dict, float]:
    """(clean GeoJSON Polygon/MultiPolygon: closed rings, shells counter-clockwise, holes clockwise, 6 decimals; total area in ha
    = parts minus holes) or raise GeomError with a plain reason."""
    t = geometry.get("type") if isinstance(geometry, dict) else None
    if t not in ("Polygon", "MultiPolygon"):
        raise GeomError(f"geometry must be a GeoJSON Polygon or MultiPolygon (got {t if t else type(geometry).__name__})")
    coords = geometry.get("coordinates")
    if not isinstance(coords, list) or not coords:
        raise GeomError(f"{t} has no coordinates")
    raw_parts = [coords] if t == "Polygon" else coords
    if len(raw_parts) > MAX_PARTS:
        raise GeomError(f"{len(raw_parts)} parts; the limit is {MAX_PARTS}")
    parts, total = [], 0
    for k, rp in enumerate(raw_parts, 1):
        if not isinstance(rp, list) or not rp:
            raise GeomError("Polygon has no coordinates")
        if len(rp) - 1 > MAX_HOLES:
            raise GeomError(f"part {k} has {len(rp) - 1} holes; the limit is {MAX_HOLES} per part")
        part = []
        for i, r in enumerate(rp):
            ring = _clean_ring(r, "a hole" if i else "a polygon")
            total += len(ring) - 1
            if total > MAX_VERTICES:
                raise GeomError(f"geometry has more than {MAX_VERTICES} vertices in total (the limit)")
            part.append(ring)
        parts.append(part)
    # one local projection for every ring, so rings can be compared with each other
    allpts = [p for part in parts for r in part for p in r]
    lat0 = sum(p[1] for p in allpts) / len(allpts)
    kx, ky = 111320 * math.cos(math.radians(lat0)), 110574
    loc = [[[(p[0] * kx, p[1] * ky) for p in r] for r in part] for part in parts]
    for part, lp in zip(parts, loc):
        for i, (r, l) in enumerate(zip(part, lp)):
            if self_intersects(r):
                raise GeomError("a hole crosses or touches itself; redraw it without crossing edges" if i else "polygon crosses or touches itself; redraw it without crossing edges")
        for i, h in enumerate(part[1:], 1):
            if _edges_hit(lp[0], lp[i]) or not all(in_ring(p[0], p[1], part[0]) for p in h):
                raise GeomError("a hole must lie fully inside its polygon and not touch its edge")
            for j in range(1, i):
                if _edges_hit(lp[j], lp[i]) or in_ring(h[0][0], h[0][1], part[j]) or in_ring(part[j][0][0], part[j][0][1], h):
                    raise GeomError("holes must not overlap or touch each other")
    for a in range(len(parts)):
        for b in range(a + 1, len(parts)):
            if any(_edges_hit(x, y) for x in loc[a] for y in loc[b]) or in_part(*parts[a][0][0], parts[b]) or in_part(*parts[b][0][0], parts[a]):
                raise GeomError(f"parts {a + 1} and {b + 1} overlap or touch; parts must be separate")
    ha = sum(part_ha(p) for p in parts)
    if ha < MIN_HA:
        raise GeomError(f"area {ha:.2f} ha is under the {MIN_HA} ha minimum (about 1.2 acres)")
    if ha > MAX_HA:
        raise GeomError(f"area {ha:,.0f} ha is over the {MAX_HA:,.0f} ha maximum (about 4,900 acres)")
    for part in parts:
        if _signed(part[0]) < 0:
            part[0].reverse()
        for h in part[1:]:
            if _signed(h) > 0:
                h.reverse()
    return to_geometry(parts), ha


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


def main_centroid(geometry):
    """Centroid of the shell of the largest part (by net area)."""
    ps = polys(geometry)
    return centroid(max(ps, key=part_ha)[0])


def sample_grid(part, max_pts=25):
    """Evenly spaced points inside the part (inside the shell, outside holes): the finest bbox grid that yields at most max_pts,
    at least 1 point. `part` is [shell, hole, ...] (a bare ring is accepted). Returns (points [[lon, lat]], interior point nearest the centroid)."""
    if part and isinstance(part[0][0], (int, float)):
        part = [part]
    ring = part[0]
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    best = []
    for n in range(2, 16):
        pts = [[min(xs) + (i + .5) * (max(xs) - min(xs)) / n, min(ys) + (j + .5) * (max(ys) - min(ys)) / n]
               for i in range(n) for j in range(n)]
        pts = [p for p in pts if in_part(p[0], p[1], part)]
        if len(pts) > max_pts:
            break
        if len(pts) >= len(best):
            best = pts
    cx, cy = centroid(ring)
    if in_part(cx, cy, part):
        inner = [cx, cy]
        if len(best) < max_pts:
            best = [inner] + best
    else:
        inner = min(best, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2) if best else [ring[0][0], ring[0][1]]
    if not best:
        best = [inner]
    return [[round(p[0], 6), round(p[1], 6)] for p in best], [round(inner[0], 6), round(inner[1], 6)]


def sample_parts(geometry, max_pts=25):
    """Sample points over all parts (budget split by net area, at least 1 each). Returns (points, interior point of the largest part)."""
    ps = polys(geometry)
    areas = [part_ha(p) for p in ps]
    tot = sum(areas) or 1
    budget = [max(1, round(max_pts * a / tot)) for a in areas]
    while sum(budget) > max_pts and max(budget) > 1:
        budget[budget.index(max(budget))] -= 1
    pts, inner = [], None
    big = areas.index(max(areas))
    for i, (p, b) in enumerate(zip(ps, budget)):
        q, ip = sample_grid(p, b)
        pts += q
        if i == big:
            inner = ip
    return pts, inner


def wkt_geom(geometry) -> str:
    """WKT POLYGON / MULTIPOLYGON of the geometry (holes included)."""
    def ring(r):
        return "(" + ",".join(f"{x:.6f} {y:.6f}" for x, y in r) + ")"
    ps = ["(" + ",".join(ring(r) for r in p) + ")" for p in polys(geometry)]
    return "POLYGON" + ps[0] if len(ps) == 1 else "MULTIPOLYGON(" + ",".join(ps) + ")"
