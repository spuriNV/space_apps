"""MODIS point series for the AI chunk from Microsoft Planetary Computer (anonymous; no Earthdata login).

Why here: B6.1's feature "NDVI minus the MODIS normal for that day of year" needs MODIS at every training
cluster of the 10 km box, not only at the field centroid (backend/nasa's AppEEARS request is one point per field).
B6.2 needs MODIS NDVI back to 2000 and MODIS LST as the ECOSTRESS fallback. The `ds` branch (spuriNV) used the
same Planetary Computer collections, downloaded by hand; this is the scripted version.

  MOD13Q1.061 (Terra, 250 m, 16-day, 2000-02..): NDVI and pixel_reliability at the 250 m pixel containing each
      training-cluster centre and the field centroid. Kept: pixel_reliability 0 (good) or 1 (marginal).
  MOD11A2.061 (Terra, 1 km, 8-day, 2000-03..): LST_Day_1km at the field centroid; QC_Day bits 0-1 in {0, 1}.
      Kelvin = DN x 0.02.

Reads only a small window around the points from each COG (sinusoidal grid); nothing else is downloaded.
Outputs data/cache/<fid>/ai/modis_pc_<product>.parquet (+ .meta.json): one row per (point, product, composite date).
Usage: uv run python -m fieldshift_ai.modis_pc [fid ...] [--product mod13q1|mod11a2] [--workers 48]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import time
from collections import defaultdict

import numpy as np
import pandas as pd
import planetary_computer as pc
import pystac_client
import rasterio
from pyproj import Transformer
from rasterio.windows import Window
from shapely.geometry import box, mapping

from .common import ai_cache, field_ids, field_polygon, now, write_json

MPC = "https://planetarycomputer.microsoft.com/api/stac/v1"
SINU = "+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +R=6371007.181 +units=m +no_defs"
PRODUCTS = {
    "mod13q1": {"collection": "modis-13Q1-061", "prefix": "MOD13Q1", "assets": {"ndvi": "250m_16_days_NDVI",
                "rel": "250m_16_days_pixel_reliability"}, "scale": {"ndvi": 1e-4}, "fill": {"ndvi": -3000}},
    "mod11a2": {"collection": "modis-11A2-061", "prefix": "MOD11A2", "assets": {"lst": "LST_Day_1km", "qc": "QC_Day"},
                "scale": {"lst": 0.02}, "fill": {"lst": 0}},
}
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2",
                GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", VSI_CACHE="TRUE")
WORKERS = 16


def points(fid: str) -> pd.DataFrame:
    """The field centroid plus the training clusters (if this field has a 10 km sample)."""
    poly = field_polygon(fid)
    rows = [{"point_id": "field", "lon": poly.centroid.x, "lat": poly.centroid.y}]
    p = ai_cache(fid) / "clusters.parquet"
    if p.exists():
        c = pd.read_parquet(p)
        rows += [{"point_id": r.cluster_id, "lon": r.lon, "lat": r.lat} for r in c.itertuples()]
    return pd.DataFrame(rows)


def _read_groups(href, groups):
    """Open one COG once; for each group of sinusoidal points read one bounding window. Returns {gid: values}."""
    last = None
    for attempt in range(4):
        try:
            res = {}
            with rasterio.Env(**GDAL_ENV), rasterio.open(href) as src:
                T = src.transform
                for gid, (xs, ys) in groups.items():
                    rr = np.floor((ys - T.f) / T.e).astype(int)
                    cc = np.floor((xs - T.c) / T.a).astype(int)
                    ok = (rr >= 0) & (cc >= 0) & (rr < src.height) & (cc < src.width)
                    vals = np.full(len(xs), np.nan)
                    if ok.any():
                        r0, r1, c0, c1 = rr[ok].min(), rr[ok].max(), cc[ok].min(), cc[ok].max()
                        a = src.read(1, window=Window(c0, r0, c1 - c0 + 1, r1 - r0 + 1))
                        vals[ok] = a[rr[ok] - r0, cc[ok] - c0]
                    res[gid] = vals
            return res
        except Exception as e:  # noqa: BLE001 - transient HTTP errors
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(str(last))


def run_many(fids, products=("mod13q1", "mod11a2")):
    """One pass over the MODIS composites for all fields: each COG is opened once and read per field."""
    t0 = time.time()
    to_sinu = Transformer.from_crs("EPSG:4326", SINU, always_xy=True)
    pts = {}
    for fid in fids:
        p = points(fid)
        x, y = to_sinu.transform(p.lon.values, p.lat.values)
        pts[fid] = (p, np.asarray(x), np.asarray(y))
    lons = np.concatenate([p.lon.values for p, _, _ in pts.values()])
    lats = np.concatenate([p.lat.values for p, _, _ in pts.values()])
    bb = box(lons.min() - 0.01, lats.min() - 0.01, lons.max() + 0.01, lats.max() + 0.01)
    cat = pystac_client.Client.open(MPC)
    rows = defaultdict(list)
    errors, n_items = [], {}
    for pk in products:
        P = PRODUCTS[pk]
        t1 = time.time()
        items = [i for i in cat.search(collections=[P["collection"]], intersects=mapping(bb),
                                       datetime="2000-01-01/2026-12-31").items() if i.id.startswith(P["prefix"])]
        n_items[pk] = len(items)
        print(f"{pk}: {len(items)} Terra items over {len(fids)} fields (search {time.time() - t1:.0f}s)", flush=True)
        groups, ids = {}, {}
        for fid, (p, x, y) in pts.items():
            sel = np.arange(len(p)) if pk == "mod13q1" else np.nonzero(p.point_id.values == "field")[0]
            groups[fid] = (x[sel], y[sel])
            ids[fid] = p.point_id.values[sel]

        def one(item):
            item = pc.sign(item)
            vals = {k: _read_groups(item.assets[a].href, groups) for k, a in P["assets"].items()}
            d = (item.properties.get("start_datetime") or item.datetime.isoformat())[:10]
            outp = {}
            for fid in groups:
                v = {k: vals[k][fid] for k in vals}
                ok = ~np.isnan(next(iter(v.values())))
                outp[fid] = [{"point_id": pid, "product": pk, "date": d, "tile": item.id.split(".")[2],
                              **{k: v[k][j] for k in v}} for j, pid in enumerate(ids[fid]) if ok[j]]
            return outp

        with cf.ThreadPoolExecutor(WORKERS) as ex:
            futs = {ex.submit(one, it): it.id for it in items}
            for k, f in enumerate(cf.as_completed(futs), 1):
                try:
                    for fid, r in f.result().items():
                        rows[fid] += r
                except Exception as e:  # noqa: BLE001
                    errors.append({"item": futs[f], "error": str(e)[:200]})
                if k % 200 == 0:
                    print(f"  {pk} {k}/{len(items)} ({time.time() - t0:.0f}s, {len(errors)} errors)", flush=True)
    for fid in fids:
        df = pd.DataFrame(rows[fid])
        if not len(df):
            continue
        if "ndvi" in df:
            raw = df["ndvi"]
            df["ndvi"] = np.where((raw == -3000) | raw.isna(), np.nan, raw * 1e-4)
            df["ndvi_good"] = df["rel"].isin([0, 1]) & df["ndvi"].notna()
        if "lst" in df:
            raw = df["lst"]
            df["lst_k"] = np.where((raw == 0) | raw.isna(), np.nan, raw * 0.02)
            df["lst_good"] = (df["qc"].fillna(3).astype(int) & 3).isin([0, 1]) & df["lst_k"].notna()
        df = df.sort_values(["point_id", "product", "date"]).groupby(["point_id", "product", "date"], as_index=False).first()
        tag = "_".join(products)
        df.to_parquet(ai_cache(fid) / f"modis_pc_{tag}.parquet", index=False)
        write_json(ai_cache(fid) / f"modis_pc_{tag}.meta.json", {
            "dataset": "modis_pc", "url": MPC, "params": {pk: PRODUCTS[pk] for pk in products},
            "fetched_at": now(), "points": "field centroid (point_id 'field') + 10 km training clusters (MOD13Q1 only)",
            "native_res_m": {"mod13q1": 250, "mod11a2": 1000}, "timestep": {"mod13q1": "16-day", "mod11a2": "8-day"},
            "units": {"ndvi": "unitless", "lst_k": "K"}, "fill_value": "NaN",
            "quality_handling": "ndvi_good: pixel_reliability in {0,1}; lst_good: QC_Day bits 0-1 in {0,1} (good or "
                                "other-quality LST produced). Platform: Terra only.",
            "auth": "none (Planetary Computer anonymous SAS token)", "n_items": n_items, "n_rows": len(df),
            "errors": errors, "seconds": round(time.time() - t0)})
        print(f"{fid}: {len(df)} rows", flush=True)
    print(f"done: {len(errors)} errors, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("fids", nargs="*")
    ap.add_argument("--product", action="append", choices=list(PRODUCTS), help="repeatable; default both")
    ap.add_argument("--workers", type=int, default=WORKERS)
    a = ap.parse_args()
    WORKERS = a.workers
    run_many(a.fids or field_ids(), tuple(a.product or PRODUCTS))
