"""GET /api/reach: how much of California's rice and forage CropLytics speaks for, from USDA NASS (reach.json, built by
build_reach.py from Quick Stats; only the derived numbers are committed)."""
from __future__ import annotations

import json
from pathlib import Path

from .sources import sn, src

DATA = Path(__file__).with_name("reach.json")
PAGE = "https://quickstats.nass.usda.gov/"


def _s(row, label):
    return src("nass", url=PAGE, title=f"USDA NASS Quick Stats: {label} ({row['source'].title()}, {row['year']})")


def build() -> dict:
    d = json.loads(DATA.read_text())
    r = d["rice_ca_planted"]
    rice = sn(r["value"], "acres", _s(r, "California rice, acres planted"), "lookup", f"{r['year']} final survey figure")
    out = {"label": "USDA NASS acres, not CropLytics measurements", "generated_at": d["generated_at"], "rice": {
        "year": r["year"], "california_planted_acres": rice}}
    cur = d.get("rice_ca_current_year")
    if cur:
        out["rice"]["current_year"] = cur["year"]
        out["rice"]["current_year_planted_acres"] = sn(cur["value"], "acres", _s(cur, "California rice, acres planted"), "lookup",
                                                       f"{cur['year']} is preliminary (September forecast)")
    counties, total = {}, 0.0
    for county, c in d["kings_tulare"].items():
        counties[county.title()] = {}
        for k, row in c.items():
            if row:
                counties[county.title()][k] = {"year": row["year"], "acres": sn(row["value"], "acres", _s(row, f"{county.title()} County, {row['desc'].lower()}"), "lookup",
                                                                                "Census of Agriculture" if row["source"] == "CENSUS" else "annual survey")}
                total += row["value"]
    hay = sum(c[k]["value"] for c in d["kings_tulare"].values() for k in ("alfalfa_hay", "other_hay") if c.get(k))
    out["forage"] = {"counties": counties, "kings_tulare_hay_acres": sn(hay, "acres", src("nass", url=PAGE, title="USDA NASS Quick Stats: Kings + Tulare County hay (alfalfa and other), acres harvested"), "computed",
                                                                        "alfalfa + other hay, both counties, latest year each (2022 Census of Agriculture)"),
                     "kings_tulare_forage_acres": sn(total, "acres", src("nass", url=PAGE, title="USDA NASS Quick Stats: Kings + Tulare County hay and silage corn, acres harvested"), "computed",
                                                     "alfalfa + other hay (2022 Census) + silage corn (2023 survey), both counties; years differ by series")}
    out["polygon_count"] = None
    out["pitch_line"] = (f"California planted about {r['value']:,.0f} acres of rice in {r['year']}; CropLytics covers every one of those fields "
                         "with the same NASA data.")
    out["pitch_line_forage"] = (f"Kings and Tulare counties harvested about {hay:,.0f} acres of hay; the same forage rotations and NASA data apply to each.")
    return out
