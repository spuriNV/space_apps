"""MODIS snow-off day of year per year, from the Salmon River watershed snow series built by backend/bc/fetch_snow.py.

Reads data/cache/bc_salmon_river_forage/modis_snow.parquet (MOD10A2 v061, 8-day maximum snow extent, watershed snow fraction)
and writes backend/nation/out/snow_off_bc_salmon_river_forage.json. Snow-off = first 8-day composite whose snow fraction is
below THRESH after the spring maximum, linearly interpolated between composites, as a day of year. This is a WATERSHED value
(1,794 km2, FWA group SALR), not a field value. Offline step; the API only reads the JSON.

Run: cd backend/api && uv run python ../nation/snow_off.py [path/to/modis_snow.parquet]
"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PID = "bc_salmon_river_forage"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[1] / "data" / "cache" / PID / "modis_snow.parquet"
THRESH = 0.5


def main():
    df = pd.read_parquet(SRC).sort_values("start")
    out = []
    for y, g in df.groupby("year"):
        g = g.dropna(subset=["snow_frac"])
        g = g[g["unclassified_frac"] < 0.6]
        if len(g) < 4:
            continue
        doy = (g["start"].dt.day_of_year + 4).to_numpy()   # composite mid-point
        f = g["snow_frac"].to_numpy()
        i0 = int(f.argmax())
        hit = None
        for i in range(i0, len(f)):
            if f[i] < THRESH:
                if i == i0 or f[i - 1] <= f[i]:
                    hit = float(doy[i])
                else:
                    hit = float(doy[i - 1] + (f[i - 1] - THRESH) / (f[i - 1] - f[i]) * (doy[i] - doy[i - 1]))
                break
        out.append({"year": int(y), "snow_off_doy": None if hit is None else round(hit), "composites_used": int(len(g)),
                    "max_snow_frac": round(float(f.max()), 2)})
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / f"snow_off_{PID}.json").write_text(json.dumps({
        "location_id": PID, "scope": "Salmon River watershed (BC FWA group SALR, 1,794 km2), not the field",
        "product": "MODIS/Terra MOD10A2 v061 8-day maximum snow extent", "product_url": "https://doi.org/10.5067/MODIS/MOD10A2.061",
        "rule": f"first 8-day composite after the spring maximum with watershed snow fraction < {THRESH}, interpolated; "
                "composites with >60% cloud or missing pixels dropped; the series starts mid-February, so a year whose snow is already "
                "below the threshold at its first composite has no result",
        "years": out}, indent=1))
    print(out[-6:])


if __name__ == "__main__":
    main()
