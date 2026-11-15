"""Build backend/api/app/week/reach.json (the numbers behind GET /api/reach) from USDA NASS Quick Stats.

    cd backend/api && uv run python -m app.week.build_reach

Needs NASS_API_KEY (environment or a .env file at the repo root, never printed). Only the derived JSON is committed.
Queries: California RICE - ACRES PLANTED (state level, annual survey); Kings and Tulare County HAY, ALFALFA and
HAY (EXCL ALFALFA) acres harvested and CORN, SILAGE acres harvested (county level; the hay numbers come from the
Census of Agriculture years, silage from the annual survey)."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("FIELDSHIFT_ROOT", HERE.parents[3]))
URL = "https://quickstats.nass.usda.gov/api/api_GET/"
PAGE = "https://quickstats.nass.usda.gov/"


def key() -> str:
    k = os.environ.get("NASS_API_KEY")
    if k:
        return k
    for env in (ROOT / ".env", ROOT.parent / "space_apps" / ".env"):  # the second is the main checkout when run from a worktree
        if env.is_file():
            for line in env.read_text().splitlines():
                if line.startswith("NASS_API_KEY=") and line.split("=", 1)[1].strip():
                    return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("NASS_API_KEY not set")


def q(k: str, **p):
    r = httpx.get(URL, params={"key": k, "format": "JSON", "year__GE": 2018, **p}, timeout=90)
    if r.status_code != 200:
        raise SystemExit(f"NASS HTTP {r.status_code}: {r.text[:120]}")
    out = []
    for d in r.json().get("data", []):
        try:
            v = float(d["Value"].replace(",", ""))
        except ValueError:
            continue
        out.append({"year": int(d["year"]), "value": v, "county": d.get("county_name"), "desc": d["short_desc"],
                    "source": d.get("source_desc"), "period": d.get("reference_period_desc")})
    return out


def latest(rows):
    return max(rows, key=lambda r: (r["year"], r["period"] == "YEAR")) if rows else None


def main():
    k = key()
    rice = q(k, commodity_desc="RICE", short_desc="RICE - ACRES PLANTED", agg_level_desc="STATE", state_alpha="CA")
    this_year = dt.date.today().year
    rice = [r for r in rice if r["period"] == "YEAR"]           # the sub-year rows are Mar/Jun acreage and Aug/Sep forecast reports
    res = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "source_url": PAGE,
           "rice_ca_planted": latest([r for r in rice if r["year"] < this_year]),     # last completed year (final)
           "rice_ca_current_year": latest([r for r in rice if r["year"] == this_year]),  # this year's survey-in-progress (preliminary)
           "rice_ca_history": sorted({(r["year"], r["value"]) for r in rice})}
    cty = {}
    for county in ("KINGS", "TULARE"):
        c = {}
        for name, com, desc in (("alfalfa_hay", "HAY", "HAY, ALFALFA - ACRES HARVESTED"),
                                ("other_hay", "HAY", "HAY, (EXCL ALFALFA) - ACRES HARVESTED"),
                                ("silage_corn", "CORN", "CORN, SILAGE - ACRES HARVESTED")):
            rows = q(k, commodity_desc=com, short_desc=desc, agg_level_desc="COUNTY", state_alpha="CA", county_name=county)
            c[name] = latest(rows)
        cty[county] = c
    res["kings_tulare"] = cty
    out = HERE / "reach.json"
    out.write_text(json.dumps(res, indent=1) + "\n")
    print("wrote", out)
    print(json.dumps({"rice": res["rice_ca_planted"], "history": res["rice_ca_history"], "counties": cty}, indent=1))


if __name__ == "__main__":
    main()
