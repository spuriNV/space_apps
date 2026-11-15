"""SoilGrids v2.0 soil composition for the BC field (ISRIC REST API, no key).

https://rest.isric.org/soilgrids/v2.0/properties/query  (docs: https://www.isric.org/explore/soilgrids/faq-soilgrids)
SoilGrids is a 250 m global machine-learning model of soil properties, not a soil survey: it is used because BC has no
field-scale soil API like California's SSURGO / Soil Data Access. Queried at the field centroid and at the corners of the
field's bounding box shrunk 25% toward the centre (5 points, about 1-2 SoilGrids cells for a 21 ha field).

Writes data/cache/bc_salmon_river_forage/soilgrids.json: per property and depth, mean of the 5 points of the median
(Q0.5) prediction with the 5-95% prediction interval (Q0.05 / Q0.95) of the centroid; units converted with the API's
d_factor (sand/silt/clay %, soc g/kg, pH, bulk density g/cm3, CEC cmol(+)/kg, coarse fragments vol %). Also a 0-30 cm and
0-100 cm depth-weighted summary and the USDA texture class from the 0-30 cm sand/silt/clay.

Run: uv run python fetch_soilgrids.py
"""
from __future__ import annotations

import time

from common import CACHE, get, now, polygon, write_json

API = "https://rest.isric.org/soilgrids/v2.0/properties/query"
PROPS = ["sand", "silt", "clay", "soc", "phh2o", "bdod", "cec", "cfvo", "nitrogen"]
DEPTHS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm"]
THICK = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15, "30-60cm": 30, "60-100cm": 40}
UNITS = {"sand": "%", "silt": "%", "clay": "%", "soc": "g/kg", "phh2o": "pH", "bdod": "g/cm3", "cec": "cmol(+)/kg",
         "cfvo": "vol %", "nitrogen": "g/kg"}


def query(lon: float, lat: float) -> dict:
    r = get(API, params=[("lon", lon), ("lat", lat)] + [("property", p) for p in PROPS] +
            [("depth", d) for d in DEPTHS] + [("value", v) for v in ("Q0.05", "Q0.5", "Q0.95", "mean")], timeout=120)
    out = {}
    for layer in r.json()["properties"]["layers"]:
        f = layer["unit_measure"]["d_factor"]
        name = layer["name"]
        for d in layer["depths"]:
            v = d["values"]
            out[(name, d["label"])] = {k: (None if v.get(k) is None else v[k] / f) for k in ("Q0.05", "Q0.5", "Q0.95", "mean")}
    return out


def usda_texture(sand: float, silt: float, clay: float) -> str:
    """USDA soil texture triangle (Soil Survey Manual, ch. 3)."""
    if silt + 1.5 * clay < 15:
        return "sand"
    if silt + 1.5 * clay >= 15 and silt + 2 * clay < 30:
        return "loamy sand"
    if (7 <= clay < 20 and sand > 52 and silt + 2 * clay >= 30) or (clay < 7 and silt < 50 and silt + 2 * clay >= 30):
        return "sandy loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "silt loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "sandy clay loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "clay loam"
    if 27 <= clay < 40 and sand <= 20:
        return "silty clay loam"
    if clay >= 35 and sand > 45:
        return "sandy clay"
    if clay >= 40 and silt >= 40:
        return "silty clay"
    return "clay"


def main():
    g, _ = polygon()
    c = g.centroid
    x0, y0, x1, y1 = g.bounds
    pts = [(c.x, c.y)] + [(c.x + 0.75 * (x - c.x), c.y + 0.75 * (y - c.y)) for x in (x0, x1) for y in (y0, y1)]
    res = []
    for lon, lat in pts:
        res.append(query(round(lon, 5), round(lat, 5)))
        time.sleep(1.5)   # ISRIC asks for at most 5 requests per minute
    layers = {}
    for p in PROPS:
        for d in DEPTHS:
            vals = [r[(p, d)]["Q0.5"] for r in res if r.get((p, d), {}).get("Q0.5") is not None]
            cen = res[0].get((p, d), {})
            layers.setdefault(p, {})[d] = {
                "median_mean_of_points": None if not vals else round(sum(vals) / len(vals), 2),
                "points_min": None if not vals else round(min(vals), 2), "points_max": None if not vals else round(max(vals), 2),
                "centroid_q05": cen.get("Q0.05"), "centroid_q50": cen.get("Q0.5"), "centroid_q95": cen.get("Q0.95"),
                "n_points": len(vals)}

    def weighted(p, depths, key="median_mean_of_points"):
        num = sum(layers[p][d][key] * THICK[d] for d in depths if layers[p][d][key] is not None)
        den = sum(THICK[d] for d in depths if layers[p][d][key] is not None)
        return None if not den else round(num / den, 2)

    top, full = DEPTHS[:3], DEPTHS
    summ = {}
    for name, ds in (("0-30cm", top), ("0-100cm", full)):
        summ[name] = {p: weighted(p, ds) for p in PROPS}
        summ[name]["low"] = {p: weighted(p, ds, "centroid_q05") for p in PROPS}
        summ[name]["high"] = {p: weighted(p, ds, "centroid_q95") for p in PROPS}
    s = summ["0-30cm"]
    tex = usda_texture(s["sand"], s["silt"], s["clay"]) if None not in (s["sand"], s["silt"], s["clay"]) else None
    write_json(CACHE / "soilgrids.json", {
        "source": {"id": "soilgrids_v2", "title": "ISRIC SoilGrids v2.0 (250 m global soil property maps), REST API",
                   "url": API, "doi": "https://doi.org/10.5194/soil-7-217-2021", "accessed": now()[:10], "verified": True,
                   "licence": "CC BY 4.0"},
        "points_lonlat": [[round(x, 5), round(y, 5)] for x, y in pts], "fetched_at": now(), "units": UNITS,
        "layers": layers, "summary": summ, "texture_class_0_30cm": tex,
        "organic_matter_pct_0_30cm": None if s["soc"] is None else round(s["soc"] / 10 * 1.724, 2),
        "notes": ["SoilGrids is a 250 m model trained on global soil profiles, not a survey of this field; its 5-95% "
                  "prediction intervals are wide. A soil test is the real answer.",
                  "Organic matter = SOC x 1.724 (van Bemmelen factor, a convention, assumed).",
                  "Drainage class, hydrologic group and available water capacity are not SoilGrids properties: they stay "
                  "unknown for this field (BC soil survey maps exist but have no query API we could use)."]})
    print("0-30cm", s, "texture", tex)


if __name__ == "__main__":
    main()
