"""NOAA CPC seasonal temp/precip outlooks (shapefiles) + seasonal/monthly drought outlook at each field.
Source: https://ftp.cpc.ncep.noaa.gov/GIS/us_tempprcpfcst/ and .../GIS/droughtlook/ (no auth).
Writes raw/ (downloads) and out/cpc.json. Fetch fresh: picks the newest seas*_YYYYMM.zip listed."""
import re, zipfile, io, sys
import shapefile
from shapely.geometry import shape, Point
from common import *

BASE = "https://ftp.cpc.ncep.noaa.gov/GIS/us_tempprcpfcst/"
DBASE = "https://ftp.cpc.ncep.noaa.gov/GIS/droughtlook/"
PAGE = {"temp": "https://www.cpc.ncep.noaa.gov/products/predictions/90day/",
        "drought": "https://www.cpc.ncep.noaa.gov/products/expert_assessment/sdo_summary.php"}
CAT = {"Above": "above normal", "Below": "below normal", "Normal": "near normal", "EC": "equal chances"}

def newest(base, pat):
    html = get(base).text
    names = sorted(set(re.findall(pat, html)))
    return names[-1]

def dl(url, sub):
    d = RAW / sub; d.mkdir(parents=True, exist_ok=True)
    z = zipfile.ZipFile(io.BytesIO(get(url, timeout=300).content)); z.extractall(d); return d

def point_rec(shp, pt, geomfn=shape):
    r = shapefile.Reader(str(shp))
    for sr in r.iterShapeRecords():
        g = geomfn(sr.shape.__geo_interface__)
        if g.contains(pt): return sr.record.as_dict()
    return None

def main():
    fetched = now()
    out = {"label": LABEL, "fetched_at": fetched,
           "source_note": "CPC GIS shapefiles on ftp.cpc.ncep.noaa.gov (the machine-readable form of the 90-day outlooks and drought outlooks).",
           "presets": {}}
    tz = newest(BASE, r"seastemp_\d{6}\.zip"); pz = newest(BASE, r"seasprcp_\d{6}\.zip")
    tu, pu = BASE + tz, BASE + pz
    td, pd_ = dl(tu, "cpc_temp"), dl(pu, "cpc_prcp")
    # drought: newest seasonal update and monthly
    sdo_up = newest(DBASE, r"sdo_update_polygons_\d{8}\.zip"); sdo = newest(DBASE, r"sdo_polygons_\d{8}\.zip"); mdo = newest(DBASE, r"mdo_polygons_\d{8}\.zip")
    sdo_use = sdo_up if sdo_up[-12:-4] >= sdo[-12:-4] else sdo
    dd = {"seasonal": dl(DBASE + sdo_use, "cpc_sdo"), "monthly": dl(DBASE + mdo, "cpc_mdo")}
    urls = {"temp": tu, "prcp": pu, "sdo": DBASE + sdo_use, "mdo": DBASE + mdo}
    out["files"] = urls
    leads = sorted([p.name for p in td.glob("lead*_*_temp.shp")], key=lambda s: int(re.match(r"lead(\d+)", s).group(1)))
    for pid in PRESETS:
        lon, lat = centroid(pid); pt = Point(lon, lat)
        res = {"point": {"lon": lon, "lat": lat}, "seasons": []}
        for f in leads:
            m = re.match(r"lead(\d+)_(\w+)_temp\.shp", f); lead, seas = int(m.group(1)), m.group(2)
            if lead > 10: continue   # NDJ 2026-27 .. ASO 2027 (covers winter + the 2027 growing season)
            row = {"lead": lead, "season": seas}
            for var, d, key in (("temp", td, "temperature"), ("prcp", pd_, "precipitation")):
                rec = point_rec(d / f"lead{lead}_{seas}_{var}.shp", pt)
                if rec is None: row[key] = None; continue
                cat = CAT[rec["Cat"]]
                url = urls[var]
                row[key] = {"category": cat, "valid_season": rec["Valid_Seas"], "issued": str(rec["Fcst_Date"]),
                    "probability": sn(None if rec["Cat"] == "EC" else rec["Prob"], "percent", url,
                        f"NOAA CPC 90-day {key} outlook", fetched, True, method="lookup",
                        note=("Equal chances: CPC gives no tilt; no probability stated" if rec["Cat"] == "EC" else
                              f"Probability of the favoured category ({cat}); CPC publishes only the favoured category probability, as a contour band (33 means 33-40). Outlook, not a forecast.")),
                    "label": LABEL}
            res["seasons"].append(row)
        dr = {}
        for kind, label in (("seasonal", "seasonal"), ("monthly", "monthly")):
            rec = point_rec(dd[kind] / "DO_Merge_Clip.shp", pt)
            u = urls["sdo" if kind == "seasonal" else "mdo"]
            dr[kind] = None if rec is None else {"category": rec["Outlook"], "target": rec["Target"], "issued": rec["Fcst_Date"], "url": u, "fetched_at": fetched, "verified": True, "label": LABEL}
            if rec is None: dr[kind] = {"category": "No drought depicted at this point (outside drought-outlook polygons or no drought)", "note": "point not inside any polygon", "url": u, "fetched_at": fetched, "verified": True, "label": LABEL}
        res["drought_outlook"] = dr
        out["presets"][pid] = res
    write_presets(OUT / "cpc.json", out)
    for pid, r in out["presets"].items():
        print(pid)
        for s in r["seasons"]:
            t, p = s["temperature"], s["precipitation"]
            print(" ", s["season"], t["valid_season"], "T:", t["category"], t["probability"]["value"], "| P:", p["category"], p["probability"]["value"])
        print("  drought", r["drought_outlook"])

if __name__ == "__main__":
    main()
