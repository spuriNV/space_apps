"""Registry-wide checks: every field in backend/fields/registry.json, every chunk's per-field output. PASS/FAIL/INFO lines.

Stdlib only:  python3 backend/fields/checks/run_checks.py
A missing output is a FAIL for steps that need no key or queue; for keyed/queued NASA steps (AppEEARS: SMAP L3, MODIS,
ECOSTRESS) it is reported as INFO "pending", because those queues can take hours and the API shows them as pending.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import fieldreg  # noqa: E402
import run_all  # noqa: E402

FIPS = {"Colusa": "06011", "Glenn": "06021", "Butte": "06007", "Sutter": "06101", "Yolo": "06113", "Kings": "06031",
        "Tulare": "06107", "Fresno": "06019", "Merced": "06047", "Stanislaus": "06099"}
SAC = {"Colusa", "Glenn", "Butte", "Sutter", "Yolo"}
SJV = {"Kings", "Tulare", "Fresno", "Merced", "Stanislaus"}
QUEUED = {"nasa.smap_l3", "nasa.modis", "nasa.ecostress"}   # AppEEARS queue
FORAGE = {"Alfalfa", "Corn", "Dbl Crop WinWht/Corn", "Dbl Crop Oats/Corn", "Dbl Crop Triticale/Corn", "Dbl Crop Barley/Corn",
          "Other Hay/Non Alfalfa", "Triticale", "Rye", "Oats"}
res = {"PASS": 0, "FAIL": 0, "INFO": 0}


def line(kind, name, detail=""):
    res[kind] += 1
    print(f"{kind} | {name}" + (f" | {detail}" if detail else ""))


def check(ok, name, detail=""):
    line("PASS" if ok else "FAIL", name, detail)


doc = json.loads(fieldreg.REGISTRY.read_text())
ids = [f["id"] for f in doc["fields"]]
check(len(ids) == len(set(ids)), "registry ids unique", f"{len(ids)} fields")
check(ids[:2] == ["car_colusa_rice", "caf_tulare_forage"], "original two first, ids kept", str(ids[:2]))
check(all(f["county"]["name"] in SAC | SJV for f in doc["fields"]), "California only (Sacramento / San Joaquin valley counties)")
for f in doc["fields"]:
    fid = f["id"]
    print(f"\n== {fid}: {f['name']} ({f['county']['name']}, {f['acres']} ac)")
    fam_ok = (f["family"] == "rice" and fid.startswith("car_") and f["county"]["name"] in SAC) or \
             (f["family"] == "forage" and fid.startswith("caf_") and f["county"]["name"] in SJV)
    check(fam_ok, f"{fid} family / id prefix / valley", f"{f['family']}, {f['county']['name']}")
    check(FIPS.get(f["county"]["name"]) == f["county"]["fips"], f"{fid} county FIPS", f["county"]["fips"])
    pp = REPO / f["polygon"]
    if not pp.exists():
        check(False, f"{fid} polygon file", f["polygon"]); continue
    props = json.loads(pp.read_text())["features"][0]["properties"]
    check(props["boundary_source"]["dwr_unique_id"] == f["dwr_unique_id"], f"{fid} polygon is DWR field {f['dwr_unique_id']}",
          props["boundary_source"]["dwr_attributes"].get("COUNTY"))
    check(props["boundary_source"]["dwr_attributes"].get("COUNTY") == f["county"]["name"], f"{fid} DWR county = registry county")
    c = props["centroid"]
    check(abs(c["lon"] - f["centroid"]["lon"]) < 1e-4 and abs(c["lat"] - f["centroid"]["lat"]) < 1e-4,
          f"{fid} centroid matches polygon", f"{c['lat']:.5f} N {c['lon']:.5f} E")
    check(abs(props["area_ha"] - f["area_ha"]) / f["area_ha"] < 0.01, f"{fid} area matches polygon", f"{props['area_ha']} ha")
    hp = REPO / "backend" / "field" / "out" / fid / "crop_history.json"
    if hp.exists():
        h = json.loads(hp.read_text())
        yrs = {int(y["year"]): y for y in h["years"]}
        rec = [yrs[y]["majority_name"] for y in range(2016, 2026) if y in yrs]
        pur = [yrs[y]["purity_pct"] for y in range(2016, 2026) if y in yrs and yrs[y]["purity_pct"] is not None]
        if f["family"] == "rice":
            ok = rec.count("Rice") >= 6
            det = f"Rice {rec.count('Rice')}/10, fallow {rec.count('Fallow/Idle Cropland')}, other {[r for r in rec if r not in ('Rice', 'Fallow/Idle Cropland')]}"
        else:
            nf = sum(r in FORAGE for r in rec)
            ok = rec.count("Alfalfa") >= 3 and nf >= 6
            det = f"Alfalfa {rec.count('Alfalfa')}/10, forage {nf}/10, other {[r for r in rec if r not in FORAGE]}"
        check(ok, f"{fid} CDL 2016-2025 history fits the {f['family']} family", det)
        check(min(pur) >= 60, f"{fid} CDL purity 2016-2025", f"min {min(pur)}%, median {sorted(pur)[len(pur) // 2]}%")
    else:
        check(False, f"{fid} crop_history.json")
    w = f.get("water") or {}
    check(bool(w.get("subbasin")), f"{fid} water: SGMA subbasin", (w.get("subbasin") or {}).get("name"))
    line("INFO" if w.get("district") is None else "PASS", f"{fid} water: district",
         w.get("district") or "no water district polygon at the centroid (DWR i03 layer)")
    for st in run_all.STEPS:
        sid = st[0]
        if run_all.done(st, fid):
            line("PASS", f"{fid} {sid}")
        elif sid in QUEUED:
            line("INFO", f"{fid} {sid}", "pending (AppEEARS queue)")
        else:
            line("FAIL", f"{fid} {sid}", "output missing")
    cm = REPO / "backend" / "ai" / "out" / fid / "calendar_ml.json"
    if cm.exists() and not fieldreg.is_original(fid):
        m = json.loads(cm.read_text())["method"]
        line("INFO", f"{fid} ML calendar model", f"from {m.get('model_from')}, field in training box: {m.get('field_in_training_box')} "
             f"({m.get('distance_from_training_box_centre_km')} km from its centre)")
print(f"---- {res['PASS']} PASS, {res['FAIL']} FAIL, {res['INFO']} INFO")
sys.exit(1 if res["FAIL"] else 0)
