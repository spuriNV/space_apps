"""MODIS snow cover over the Salmon River (Shuswap) watershed, spring of every year 2001-2026 (no key).

Product: NASA MOD10A2 v061 (Terra, 500 m, 8-day maximum snow extent), the Cloud-Optimized GeoTIFFs on Microsoft Planetary
Computer (collection `modis-10A2-061`, tile h10v03; anonymous SAS token). An 8-day composite rather than daily MOD10A1 because
it removes most cloud for the cost of one read per 8 days.
Watershed: BC Freshwater Atlas watershed group SALR "Salmon River" (WHSE_BASEMAPPING.FWA_WATERSHED_GROUPS_POLY, 1,794 km2),
which is the river's basin to Shuswap Lake (a little larger than the 1,555 km2 above gauge 08LE021).

Per composite: snow fraction = pixels "snow" (200) / pixels with a decision (snow 200 + no snow 25); cloud (50), night,
missing and water are excluded and their share is kept as `unclassified_frac`.

Writes data/cache/bc_salmon_river_forage/modis_snow.parquet (year, start, end, snow_frac, unclassified_frac, n_pixels),
modis_snow.meta.json and salmon_watershed.geojson (the SALR outline, simplified to 100 m, for the map).
Run: cd backend/bc && uv run python fetch_snow.py
"""
from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds
from shapely.geometry import mapping, shape
from shapely.ops import transform as stransform
from pyproj import Transformer

from common import CACHE, get, now, write_json

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLL = "modis-10A2-061"
WFS = "https://openmaps.gov.bc.ca/geo/pub/wfs"
YEARS = range(2001, 2027)
DOY = (49, 177)   # composites starting 18 Feb .. 26 Jun


def watershed():
    r = get(WFS, params={"service": "WFS", "version": "2.0.0", "request": "GetFeature",
                         "typeName": "WHSE_BASEMAPPING.FWA_WATERSHED_GROUPS_POLY", "outputFormat": "application/json",
                         "srsName": "EPSG:4326", "CQL_FILTER": "WATERSHED_GROUP_CODE='SALR'"})
    f = r.json()["features"][0]
    return shape(f["geometry"]), f["properties"]


def items():
    import requests
    keep = []
    for y in YEARS:   # one search per spring keeps each answer under the page limit
        body = {"collections": [COLL], "intersects": {"type": "Point", "coordinates": [-119.45, 50.55]},
                "datetime": f"{y}-02-15T00:00:00Z/{y}-06-30T00:00:00Z", "limit": 100}
        r = requests.post(f"{STAC}/search", json=body, timeout=120)
        r.raise_for_status()
        for it in r.json()["features"]:
            s = pd.Timestamp(it["properties"]["start_datetime"]).tz_convert(None)
            if it["id"].startswith("MOD10A2") and DOY[0] <= s.dayofyear <= DOY[1]:
                keep.append({"start": s, "end": pd.Timestamp(it["properties"]["end_datetime"]).tz_convert(None),
                             "href": it["assets"]["Maximum_Snow_Extent"]["href"], "id": it["id"]})
    return pd.DataFrame(keep).drop_duplicates("start").sort_values("start")


def main():
    geom, props = watershed()
    tok = get("https://planetarycomputer.microsoft.com/api/sas/v1/token/modiseuwest/modis-061-cogs").json()["token"]
    its = items()
    print(len(its), "composites")
    with rasterio.open(f"{its.iloc[0].href}?{tok}") as src:
        crs = src.crs
    tr = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
    g = stransform(tr, geom)

    def one(row):
        try:
            with rasterio.open(f"{row.href}?{tok}") as src:
                w = from_bounds(*g.bounds, transform=src.transform).round_offsets().round_lengths()
                a = src.read(1, window=w)
                inside = ~geometry_mask([mapping(g)], out_shape=a.shape, transform=src.window_transform(w))
        except Exception as e:  # noqa: BLE001
            print("fail", row.id, e)
            return None
        v = a[inside]
        snow, land = int((v == 200).sum()), int((v == 25).sum())
        dec = snow + land
        return {"year": row.start.year, "start": row.start, "end": row.end, "granule": row.id,
                "snow_frac": snow / dec if dec else np.nan, "unclassified_frac": 1 - dec / len(v), "n_pixels": int(len(v))}

    with ThreadPoolExecutor(8) as ex:
        rows = [r for r in ex.map(one, its.itertuples()) if r]
    df = pd.DataFrame(rows).sort_values("start").reset_index(drop=True)
    df.to_parquet(CACHE / "modis_snow.parquet", index=False)
    simp = geom.simplify(0.001)
    write_json(CACHE / "salmon_watershed.geojson", {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": mapping(simp), "properties": {
            "code": props["WATERSHED_GROUP_CODE"], "name": props["WATERSHED_GROUP_NAME"], "area_ha": props["AREA_HA"],
            "source": "BC Freshwater Atlas watershed groups (WHSE_BASEMAPPING.FWA_WATERSHED_GROUPS_POLY)"}}]})
    write_json(CACHE / "modis_snow.meta.json", {
        "title": "MODIS/Terra Snow Cover 8-Day L3 Global 500m (MOD10A2 v061) over the Salmon River watershed (FWA group SALR)",
        "url": f"{STAC}/collections/{COLL}", "product_doi": "https://doi.org/10.5067/MODIS/MOD10A2.061",
        "fetched_at": now(), "auth": "Planetary Computer anonymous SAS token",
        "watershed": {"code": "SALR", "area_km2": round(props["AREA_HA"] / 100, 1), "wfs": WFS},
        "params": {"years": [min(YEARS), max(YEARS)], "composite_start_doy": list(DOY), "platform": "terra"},
        "rows": len(df), "units": {"snow_frac": "fraction of classified watershed pixels mapped as snow"},
        "quality_handling": "Maximum_Snow_Extent: 200 snow, 25 no snow are classified; cloud 50, night 11, missing 0/1, "
                            "water 37/39/100, 254/255 excluded (unclassified_frac)."})
    print(df.groupby("year").snow_frac.apply(lambda s: list(s.round(2))).tail(5))


if __name__ == "__main__":
    main()
