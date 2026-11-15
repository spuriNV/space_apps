"""Look up each registry field's water source from public boundary layers and write it into registry.json (`water`).

Stdlib only, no key. Run from anywhere:  python3 backend/fields/water_sources.py [field_id ...]

Layers (DWR ArcGIS REST, gis.water.ca.gov, queried at the field's polygon centroid):
  - Water districts: Boundaries/i03_WaterDistricts (all public water agencies; several can overlap a point)
  - Bulletin 118 subbasin: Geoscientific/i08_B118_CA_GroundwaterBasins
  - SGMA 2019 basin priority: Geoscientific/i08_B118_SGMA_2019_Basin_Prioritization (layer 1)
  - Critically overdrafted basins: Geoscientific/i08_CriticallyOverdraftedBasins
  - GSA: Boundaries/i03_Groundwater_Sustainability_Agencies
  - GSP status (DWR assessment): Boundaries/i03_Groundwater_Sustainability_Plan_Areas, by subbasin number
  - Adjudicated areas: Boundaries/i03_Adjudicated_Areas
State Water Board probation: the basin list on https://www.waterboards.ca.gov/water_issues/programs/sgma/groundwater_basins/
(text between "designated the following basins probationary:" and the next heading). Anything that can't be reached is
stored as null with the error, never guessed.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fieldreg  # noqa: E402

GIS = "https://gis.water.ca.gov/arcgis/rest/services"
L = {
    "districts": f"{GIS}/Boundaries/i03_WaterDistricts/FeatureServer/0",
    "b118": f"{GIS}/Geoscientific/i08_B118_CA_GroundwaterBasins/FeatureServer/0",
    "priority": f"{GIS}/Geoscientific/i08_B118_SGMA_2019_Basin_Prioritization/MapServer/1",
    "cod": f"{GIS}/Geoscientific/i08_CriticallyOverdraftedBasins/FeatureServer/0",
    "gsa": f"{GIS}/Boundaries/i03_Groundwater_Sustainability_Agencies/FeatureServer/0",
    "gsp": f"{GIS}/Boundaries/i03_Groundwater_Sustainability_Plan_Areas/FeatureServer/0",
    "adjudicated": f"{GIS}/Boundaries/i03_Adjudicated_Areas/FeatureServer/0",
}
SWRCB = "https://www.waterboards.ca.gov/water_issues/programs/sgma/groundwater_basins/"
UA = {"User-Agent": "Mozilla/5.0 (CropLytics hackathon; water source lookup)"}
AG_WORDS = ("irrigation", "water district", "water storage", "reclamation", "canal", "water agency", "water authority",
            "mutual water", "ditch", "water company", "resource conservation")


def get(url, params=None, timeout=60):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def at_point(layer, lon, lat, fields="*", distance_m=0):
    q = {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326,
         "spatialRel": "esriSpatialRelIntersects", "outFields": fields, "returnGeometry": "false", "f": "json"}
    if distance_m:
        q.update(distance=distance_m, units="esriSRUnit_Meter")
    d = json.loads(get(L[layer] + "/query", q))
    if "error" in d:
        raise RuntimeError(d["error"])
    return [f["attributes"] for f in d.get("features", [])]


def where(layer, clause, fields="*"):
    d = json.loads(get(L[layer] + "/query", {"where": clause, "outFields": fields, "returnGeometry": "false", "f": "json"}))
    if "error" in d:
        raise RuntimeError(d["error"])
    return [f["attributes"] for f in d.get("features", [])]


def ms(v):
    return dt.datetime.fromtimestamp(v / 1000, dt.timezone.utc).date().isoformat() if isinstance(v, (int, float)) else v


def swrcb_status():
    """{'probationary': [...], 'under_evaluation': [...], 'returned_to_dwr': [...]} from the State Water Board basin page."""
    s = get(SWRCB).decode("utf-8", "ignore")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S)
    t = re.sub(r"<[^>]+>", " | ", t)
    t = re.sub(r"\s+", " ", t)

    def names(start, stop):
        i = t.find(start)
        if i < 0:
            return None
        j = t.find(stop, i + len(start))
        chunk = t[i + len(start): j if j > 0 else i + 600]
        return sorted({m.strip() for m in re.findall(r"([A-Z][A-Za-z\-\. ]+? Subbasin)", chunk)})

    return {
        "probationary": names("designated the following basins probationary:", "Basins Returned"),
        "under_evaluation": names("for a potential probationary designation:", "Basins Designated"),
        "returned_to_dwr": names("Basins Returned to Department of Water Resources", "Basins Under"),
    }


def lookup(fid, probation, today):
    f = fieldreg.get(fid)
    lon, lat = f["centroid"]["lon"], f["centroid"]["lat"]
    w = {"looked_up": today, "point": [lon, lat], "method": "layers queried at the field's polygon centroid", "errors": {}}
    try:
        ds = at_point("districts", lon, lat, "AGENCYNAME,AGENCYUNIQUEID,SOURCE,Date_Data_Applies_To")
        names = sorted({d["AGENCYNAME"].strip() for d in ds if d.get("AGENCYNAME")},
                       key=lambda n: (not any(k in n.lower() for k in AG_WORDS), n))
        w["district"] = names[0] if names else None
        w["other_agencies"] = names[1:]
        w["district_source"] = {"title": "DWR i03 Water Districts", "url": L["districts"], "accessed": today, "verified": True}
        if not names:   # no agency at the centroid: name the nearest one(s) so the panel can say "outside X, ~N km"
            w["nearest_district"] = None
            for m in (1000, 2000, 5000):
                near = at_point("districts", lon, lat, "AGENCYNAME", distance_m=m)
                nn = sorted({d["AGENCYNAME"].strip() for d in near if d.get("AGENCYNAME")},
                            key=lambda n: (not any(k in n.lower() for k in AG_WORDS), n))
                if nn:
                    w["nearest_district"] = {"name": nn[0], "within_m": m, "others": nn[1:],
                                             "note": f"the field centroid is in no DWR water district; {nn[0]} is within {m} m"}
                    break
    except Exception as e:  # noqa: BLE001
        w["district"] = None
        w["errors"]["districts"] = str(e)[:200]
    try:
        b = at_point("b118", lon, lat, "Basin_Subbasin_Number,Basin_Subbasin_Name,Basin_Name")
        w["subbasin"] = {"number": b[0]["Basin_Subbasin_Number"], "name": b[0]["Basin_Subbasin_Name"],
                         "basin": b[0]["Basin_Name"]} if b else None
        w["subbasin_source"] = {"title": "DWR Bulletin 118 groundwater basins (i08_B118_CA_GroundwaterBasins)",
                                "url": L["b118"], "accessed": today, "verified": True}
    except Exception as e:  # noqa: BLE001
        w["subbasin"] = None
        w["errors"]["b118"] = str(e)[:200]
    num = (w.get("subbasin") or {}).get("number")
    try:
        pr = at_point("priority", lon, lat, "*")
        pv = next((v for r in pr for k, v in r.items() if k.endswith(".Priority")), None)
        w["sgma_priority"] = pv
        w["sgma_priority_source"] = {"title": "DWR SGMA 2019 Basin Prioritization", "url": L["priority"], "accessed": today, "verified": True}
    except Exception as e:  # noqa: BLE001
        w["sgma_priority"] = None
        w["errors"]["priority"] = str(e)[:200]
    try:
        c = at_point("cod", lon, lat, "Basin_Subbasin_Number,critical_flag")
        w["critically_overdrafted"] = bool(c) and any(str(x.get("critical_flag", "")).strip().lower() in ("y", "yes", "1", "true") or
                                                      x.get("critical_flag") is None for x in c)
        w["critically_overdrafted_source"] = {"title": "DWR critically overdrafted basins", "url": L["cod"], "accessed": today, "verified": True}
    except Exception as e:  # noqa: BLE001
        w["critically_overdrafted"] = None
        w["errors"]["cod"] = str(e)[:200]
    try:
        g = at_point("gsa", lon, lat, "GSA_ID,GSA_Name,GSA_URL,Exclusive,Basin_Subbasin_Number")
        w["gsa"] = [{"name": x["GSA_Name"].strip(), "id": x["GSA_ID"], "url": (x.get("GSA_URL") or "").strip() or None,
                     "exclusive": x.get("Exclusive")} for x in g]
        w["gsa_source"] = {"title": "DWR SGMA Portal, Groundwater Sustainability Agencies (i03)", "url": L["gsa"], "accessed": today, "verified": True}
    except Exception as e:  # noqa: BLE001
        w["gsa"] = None
        w["errors"]["gsa"] = str(e)[:200]
    try:
        gp = where("gsp", f"Basin_Subbasin_Number='{num}'", "GSP_ID,Status,Submitted,UPDATED_DT,GSA_IDs") if num else []
        w["gsp"] = [{"gsp_id": x["GSP_ID"], "dwr_status": x.get("Status"), "submitted": ms(x.get("Submitted")),
                     "updated": ms(x.get("UPDATED_DT"))} for x in gp]
        w["gsp_source"] = {"title": "DWR SGMA Portal, Groundwater Sustainability Plan areas (i03)", "url": L["gsp"], "accessed": today, "verified": True}
    except Exception as e:  # noqa: BLE001
        w["gsp"] = None
        w["errors"]["gsp"] = str(e)[:200]
    try:
        a = at_point("adjudicated", lon, lat, "NAME")
        w["adjudicated_area"] = a[0]["NAME"] if a else None
    except Exception as e:  # noqa: BLE001
        w["adjudicated_area"] = None
        w["errors"]["adjudicated"] = str(e)[:200]
    # State Water Board probation, matched on the subbasin's short name ("SAN JOAQUIN VALLEY - TULARE LAKE" -> "Tulare Lake")
    short = ((w.get("subbasin") or {}).get("name") or "").split(" - ")[-1].strip().lower()
    if probation is None:
        w["state_board"] = None
    else:
        st = "not listed (DWR jurisdiction)"
        for k, label in (("probationary", "probationary"), ("under_evaluation", "under evaluation for probation"),
                         ("returned_to_dwr", "returned to DWR")):
            if any(n.lower().removesuffix(" subbasin") == short for n in probation.get(k) or []):
                st = label
        w["state_board"] = {"status": st, "url": SWRCB, "accessed": today, "verified": True,
                            "listed": probation}
    if not w["errors"]:
        del w["errors"]
    return w


def main():
    today = dt.date.today().isoformat()
    try:
        probation = swrcb_status()
    except Exception as e:  # noqa: BLE001
        print("State Water Board page not reached:", e)
        probation = None
    doc = json.loads(fieldreg.REGISTRY.read_text())
    want = sys.argv[1:] or [f["id"] for f in doc["fields"]]
    for f in doc["fields"]:
        if f["id"] in want:
            f["water"] = lookup(f["id"], probation, today)
            w = f["water"]
            print(f"{f['id']}: {w.get('district')} | {(w.get('subbasin') or {}).get('name')} {(w.get('subbasin') or {}).get('number')} "
                  f"| priority {w.get('sgma_priority')} | GSA {[g['name'] for g in w.get('gsa') or []]} "
                  f"| GSP {[g['dwr_status'] for g in w.get('gsp') or []]} | board {(w.get('state_board') or {}).get('status')} "
                  f"| COD {w.get('critically_overdrafted')} | errors {w.get('errors')}")
    fieldreg.REGISTRY.write_text(json.dumps(doc, indent=1) + "\n")


if __name__ == "__main__":
    main()
