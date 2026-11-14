"""Shared helpers: .env loading, presets, cache writing, AppEEARS client."""
from __future__ import annotations

import io
import json
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from shapely.geometry import shape
from shapely.ops import unary_union

REPO = Path(__file__).resolve().parents[3]
POLYGONS = REPO / "backend" / "field" / "polygons"
CACHE = REPO / "data" / "cache"
PRESETS = ["car_colusa_rice", "caf_tulare_forage"]
BLOCKED_MSG = "BLOCKED: no Earthdata credentials in .env"
APPEEARS = "https://appeears.earthdatacloud.nasa.gov/api"


def load_env() -> bool:
    """Load repo-root .env into os.environ (never prints values). True if Earthdata creds present."""
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO / ".env", override=False)
    except Exception:
        pass
    return bool(os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD"))


def require_creds() -> None:
    """Call first in every fetcher: exits 0 cleanly when .env is missing."""
    if not load_env():
        print(BLOCKED_MSG)
        sys.exit(0)


def field_geometry(preset: str):
    d = json.loads((POLYGONS / f"{preset}.geojson").read_text())
    geoms = [shape(f["geometry"]) for f in d["features"]]
    return unary_union(geoms)


def field_point(preset: str) -> tuple[float, float]:
    """(lon, lat) of the polygon centroid (EPSG:4326, lon first)."""
    c = field_geometry(preset).centroid
    return round(c.x, 6), round(c.y, 6)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_cache(preset: str, dataset: str, df: pd.DataFrame, meta: dict) -> Path:
    out = CACHE / preset
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / f"{dataset}.parquet", index=False)
    meta = {**meta, "fetched_at": now_iso(), "n_rows": int(len(df)),
            "footprint_geojson": json.loads(json.dumps(field_geometry(preset).__geo_interface__)),
            "auth": "NASA Earthdata Login (credentials from repo-root .env, not stored)"}
    (out / f"{dataset}.meta.json").write_text(json.dumps(meta, indent=1, default=str))
    print(f"[{preset}] wrote {dataset}.parquet ({len(df)} rows)")
    return out / f"{dataset}.parquet"


# ---------------------------------------------------------------- AppEEARS
class AppEEARS:
    def __init__(self) -> None:
        r = requests.post(f"{APPEEARS}/login",
                          auth=(os.environ["EARTHDATA_USERNAME"], os.environ["EARTHDATA_PASSWORD"]), timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"AppEEARS login failed HTTP {r.status_code}: {r.text[:300]}. "
                               "Fix: log in once at https://appeears.earthdatacloud.nasa.gov and accept its terms; "
                               "approve the 'AppEEARS' application in your Earthdata profile.")
        self.h = {"Authorization": f"Bearer {r.json()['token']}"}

    def submit_point(self, name: str, lon: float, lat: float, start: str, end: str,
                     layers: list[tuple[str, str]]) -> str:
        """start/end 'YYYY-MM-DD'. layers: [(product.version, layer)]."""
        fmt = lambda s: datetime.strptime(s, "%Y-%m-%d").strftime("%m-%d-%Y")
        body = {"task_type": "point", "task_name": name,
                "params": {"dates": [{"startDate": fmt(start), "endDate": fmt(end)}],
                           "layers": [{"product": p, "layer": l} for p, l in layers],
                           "coordinates": [{"id": "field", "longitude": lon, "latitude": lat, "category": "field"}]}}
        r = requests.post(f"{APPEEARS}/task", json=body, headers=self.h, timeout=120)
        if r.status_code >= 300:
            raise RuntimeError(f"AppEEARS task submit HTTP {r.status_code}: {r.text[:400]}")
        return r.json()["task_id"]

    def wait(self, task_id: str, poll: int = 30, timeout: int = 6 * 3600) -> None:
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                r = requests.get(f"{APPEEARS}/task/{task_id}", headers=self.h, timeout=60)
                r.raise_for_status()
                st = r.json().get("status")
            except Exception as e:  # noqa: BLE001  transient: keep polling
                print(f"  poll error {type(e).__name__}; retrying", flush=True)
                time.sleep(poll)
                continue
            if st == "done":
                return
            if st in ("error", "failed"):
                raise RuntimeError(f"AppEEARS task {task_id} {st}: {r.text[:400]}")
            time.sleep(poll)
        raise TimeoutError(f"AppEEARS task {task_id} not done after {timeout}s")

    def results(self, task_id: str) -> dict[str, pd.DataFrame]:
        """Download all CSVs in the bundle; returns {filename: DataFrame}."""
        b = requests.get(f"{APPEEARS}/bundle/{task_id}", headers=self.h, timeout=60)
        b.raise_for_status()
        out = {}
        for f in b.json()["files"]:
            if f["file_name"].lower().endswith(".csv"):
                r = requests.get(f"{APPEEARS}/bundle/{task_id}/{f['file_id']}", headers=self.h, timeout=600)
                r.raise_for_status()
                out[f["file_name"]] = pd.read_csv(io.BytesIO(r.content))
        return out

    def submit_points(self, name: str, points: dict[str, tuple[float, float]], start: str, end: str,
                      layers: list[tuple[str, str]]) -> str:
        fmt = lambda s: datetime.strptime(s, "%Y-%m-%d").strftime("%m-%d-%Y")
        body = {"task_type": "point", "task_name": name,
                "params": {"dates": [{"startDate": fmt(start), "endDate": fmt(end)}],
                           "layers": [{"product": p, "layer": l} for p, l in layers],
                           "coordinates": [{"id": k, "longitude": lo, "latitude": la, "category": "field"}
                                           for k, (lo, la) in points.items()]}}
        r = requests.post(f"{APPEEARS}/task", json=body, headers=self.h, timeout=120)
        if r.status_code >= 300:
            raise RuntimeError(f"AppEEARS task submit HTTP {r.status_code}: {r.text[:400]}")
        return r.json()["task_id"]

    def multi_point(self, dataset: str, points: dict[str, tuple[float, float]], start: str, end: str,
                    layers: list[tuple[str, str]], resume: bool = True) -> tuple[dict[str, pd.DataFrame], dict]:
        """One AppEEARS point task for all points and the whole date range. The task id is saved in
        data/cache/_appeears/<dataset>.task.json and every bundle CSV in data/cache/_appeears/<dataset>/ so a rerun
        resumes the same task (no resubmission) and parsing can be redone offline.
        Returns ({point_id: frame with 'Date' + one column per layer (bare layer name)}, extra)."""
        raw = CACHE / "_appeears"
        raw.mkdir(parents=True, exist_ok=True)
        state_f = raw / f"{dataset}.task.json"
        params = {"points": points, "start": start, "end": end, "layers": layers}
        tid = None
        if resume and state_f.exists():
            st = json.loads(state_f.read_text())
            if st.get("params") == json.loads(json.dumps(params)):
                tid = st["task_id"]
                print(f"  resuming AppEEARS task {tid} for {dataset}", flush=True)
        if tid is None:
            tid = self.submit_points(f"fs_{dataset}_{start}_{end}", points, start, end, layers)
            state_f.write_text(json.dumps({"task_id": tid, "params": params, "submitted": now_iso()}, indent=1))
            print(f"  submitted {dataset} {start}..{end}: task {tid}", flush=True)
        self.wait(tid)
        res = self.results(tid)
        d = raw / dataset
        d.mkdir(exist_ok=True)
        for k, v in res.items():
            v.to_csv(d / k, index=False)
        mains = [v for k, v in res.items() if k.endswith("-results.csv")]
        if not mains:
            raise RuntimeError(f"no *-results.csv in AppEEARS bundle {tid}: {list(res)}")
        df = pd.concat(mains, ignore_index=True)
        ren = {}
        for _, layer in layers:
            for c in df.columns:
                if c.endswith(layer) and c not in ren and not c.endswith("_" + layer + "_Description"):
                    ren[c] = layer
        df = df.rename(columns=ren)
        idcol = "ID" if "ID" in df.columns else None
        out = {k: (df[df[idcol] == k].copy() if idcol else df.copy()) for k in points}
        return out, {"task_ids": [tid], "raw_dir": str(d.relative_to(REPO))}


def clean_appeears_df(df: pd.DataFrame, layers: list[str], fill: dict[str, float]) -> pd.DataFrame:
    keep = ["Date"] + [l for l in layers if l in df.columns]
    out = df.loc[:, ~df.columns.duplicated()][keep].copy()
    dt = pd.to_datetime(out.pop("Date"))
    out["date"] = dt.dt.tz_convert(None) if dt.dt.tz is not None else dt  # AppEEARS dates are UTC strings
    for l, fv in fill.items():
        if l in out.columns:
            out.loc[out[l] == fv, l] = float("nan")
    return out.sort_values("date").reset_index(drop=True)


def common_args(desc: str):
    import argparse
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("--preset", choices=PRESETS, action="append", help="default: both")
    ap.add_argument("--start", help="YYYY-MM-DD override")
    ap.add_argument("--end", help="YYYY-MM-DD override")
    ap.add_argument("--limit", type=int, help="smoke test: only first N granules/scenes")
    return ap


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
