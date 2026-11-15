from __future__ import annotations
import datetime as dt, json
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
FIELD = REPO / "backend" / "field"
CACHE = REPO / "data" / "cache"
OUT = HERE / "out"
import sys as _sys
_sys.path.insert(0, str(REPO / "backend" / "fields"))
import fieldreg  # noqa: E402
PRESETS = fieldreg.selected()   # registry fields (FIELDSHIFT_FIELDS limits the list)
WORK = "EPSG:32610"
MPC = "https://planetarycomputer.microsoft.com/api/stac/v1"
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF,.tiff",
                GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2")

def today(): return dt.date.today().isoformat()
def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

def load_polygon(preset):
    f = json.load(open(FIELD / "polygons" / f"{preset}.geojson"))["features"][0]
    return shape(f["geometry"]), f["properties"]

def polygon_in(preset, epsg):
    g, _ = load_polygon(preset)
    t = Transformer.from_crs("EPSG:4326", epsg, always_xy=True)
    return transform(t.transform, g)

def write_json(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, default=str))

def sn(value, unit, source, method="computed", note="", verified=True, low=None, high=None):
    return {"value": None if value is None else round(float(value), 3), "unit": unit, "low": low, "high": high,
            "method": method, "source": source, "note": note, "verified": verified}
