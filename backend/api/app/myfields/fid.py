"""Self-contained field ids: `my_<base64url(zlib(JSON))>`. The id carries the name and the outline, so any server can
decode it and recompute; nothing has to persist server-side.

JSON {"v":1,"n":name,"c":[x0,y0,dx1,dy1,...]}: corners in integer units of 1e-5 degrees (about 1 m), the first as an
absolute value, the rest as deltas from the previous corner (the closing corner is implied). Deltas keep a 200-corner
outline well under the length limit; if it is still too long the outline is simplified (Douglas-Peucker, 5 m, doubling).
"""
from __future__ import annotations

import base64
import json
import math
import re
import zlib

from . import geom as G

PREFIX = "my_"
MAX_ID = 1800
MAX_NAME = 60
ID_RE = re.compile(r"^my_[A-Za-z0-9_-]{8,%d}$" % (MAX_ID + 100))


class BadId(ValueError):
    pass


def clean_name(name) -> str:
    n = re.sub(r"\s+", " ", str(name or "")).strip()[:MAX_NAME]
    if not n:
        raise G.GeomError("name is required (1-%d characters)" % MAX_NAME)
    return n


def _pack(name, ring):
    pts = [(round(p[0] * 1e5), round(p[1] * 1e5)) for p in ring[:-1]]
    flat, px, py = [], 0, 0
    for x, y in pts:
        flat += [x - px, y - py]; px, py = x, y
    raw = json.dumps({"v": 1, "n": name, "c": flat}, separators=(",", ":"), ensure_ascii=False).encode()
    return PREFIX + base64.urlsafe_b64encode(zlib.compress(raw, 9)).rstrip(b"=").decode()


def _dp(pts, tol):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    best, bi = -1.0, 0
    for i in range(1, len(pts) - 1):
        px, py = pts[i]
        d = math.hypot(px - x1, py - y1) if L == 0 else abs(dx * (y1 - py) - dy * (x1 - px)) / L
        if d > best:
            best, bi = d, i
    if best <= tol:
        return [pts[0], pts[-1]]
    return _dp(pts[:bi + 1], tol)[:-1] + _dp(pts[bi:], tol)


def _simplify(ring, tol_m):
    lat0 = sum(p[1] for p in ring) / len(ring)
    kx, ky = 111320 * math.cos(math.radians(lat0)), 110574
    xy = [(p[0] * kx, p[1] * ky) for p in ring]
    keep = _dp(xy, tol_m)
    idx = []
    j = 0
    for k in keep:                       # map back to the original corners (order preserved)
        while xy[j] != k:
            j += 1
        idx.append(j)
    return [ring[i] for i in idx]


def encode(name, geometry) -> tuple[str, dict, float, dict | None]:
    """(id, clean Polygon, area ha, simplification note or None). Raises GeomError (-> 422)."""
    name = clean_name(name)
    geometry = json.loads(json.dumps(geometry))
    try:
        for p in geometry["coordinates"][0]:
            p[0], p[1] = round(float(p[0]), 5), round(float(p[1]), 5)
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    poly, ha = G.validate(geometry)
    ring = poly["coordinates"][0]
    note, tol, n0 = None, 5.0, len(ring) - 1
    fid = _pack(name, ring)
    while len(fid) > MAX_ID:
        if tol > 200 or len(ring) <= 4:
            raise G.GeomError("this outline is too detailed to store in a share link; draw it with fewer corners")
        cand = _simplify(ring, tol)
        tol *= 2
        if len(cand) < 4:
            continue
        try:
            poly, ha = G.validate({"type": "Polygon", "coordinates": [cand]})
        except G.GeomError:
            continue
        ring = poly["coordinates"][0]
        fid = _pack(name, ring)
        note = {"simplified": True, "corners_before": n0, "corners_after": len(ring) - 1, "tolerance_m": tol / 2,
                "reason": f"the outline was simplified so the field id stays under {MAX_ID} characters"}
    return fid, poly, ha, note


def decode(fid: str) -> tuple[str, dict, float]:
    """(name, Polygon, area ha) or raise BadId (-> 400)."""
    if not isinstance(fid, str) or not ID_RE.match(fid):
        raise BadId(f"not a field id: expected my_ followed by up to {MAX_ID} URL-safe characters")
    try:
        b = fid[len(PREFIX):]
        raw = zlib.decompressobj().decompress(base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)), 40000)
        d = json.loads(raw)
        if d.get("v") != 1:
            raise BadId(f"unknown field id version {d.get('v')!r}")
        name, flat = clean_name(d["n"]), d["c"]
        if len(flat) % 2 or not 6 <= len(flat) <= 2 * G.MAX_VERTICES or not all(isinstance(v, int) for v in flat):
            raise ValueError("bad corner list")
        x = y = 0
        ring = []
        for i in range(0, len(flat), 2):
            x += flat[i]; y += flat[i + 1]
            ring.append([x / 1e5, y / 1e5])
        poly, ha = G.validate({"type": "Polygon", "coordinates": [ring]})
    except BadId:
        raise
    except G.GeomError as e:
        raise BadId(f"field id decodes to an invalid outline: {e}")
    except Exception as e:  # noqa: BLE001
        raise BadId(f"field id is corrupt or truncated ({type(e).__name__}); open it from a fresh share link")
    return name, poly, ha
