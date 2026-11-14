"""USDA RMA cause-of-loss: download colsom_YYYY.zip 2010-2024, keep CA rows, compute indemnity shares by cause."""
import io, json, sys, zipfile, collections
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[3]
BASE = "https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business/cause_of_loss"
PAGE = "https://www.rma.usda.gov/tools-reports/summary-of-business/cause-loss"
LAYOUT = f"{BASE}/COL_Summary_of_Business_with_Month_All_Years.pdf"
YEARS = list(range(2010, 2025))
RAW = Path(__file__).resolve().parents[1] / "out" / "_rma_raw"
GROUPS = {  # cause description -> group (our grouping; documented in README)
    "drought": ["Drought", "Failure of Irrigation Supply"],
    "excess_moisture": ["Excess Moisture/Precipitation/Rain", "Flood", "Cold Wet Weather"],
    "heat": ["Heat", "Hot Wind"],
}
# (preset, county fips, county label, crop key, commodity-name predicate)
PROFILES = {
    "car_colusa_rice": [("011", "Colusa", "rice", lambda n: n == "Rice")],
    "caf_tulare_forage": [
        ("031", "Kings", "alfalfa_forage", lambda n: n.lower().startswith(("alfalfa", "forage production", "pasture,rangeland,forage")) and "seed" not in n.lower()),
        ("107", "Tulare", "alfalfa_forage", lambda n: n.lower().startswith(("alfalfa", "forage production", "pasture,rangeland,forage")) and "seed" not in n.lower()),
        ("031", "Kings", "corn", lambda n: n == "Corn"),
        ("107", "Tulare", "corn", lambda n: n == "Corn"),
    ],
}

def group_of(cause):
    for g, lst in GROUPS.items():
        if cause in lst: return g
    return "other"

def load_year(y):
    RAW.mkdir(parents=True, exist_ok=True)
    cache = RAW / f"ca_{y}.json"
    if cache.exists(): return json.load(open(cache))
    url = f"{BASE}/colsom_{y}.zip"
    r = requests.get(url, timeout=300); r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    rows = []
    for n in z.namelist():
        for line in z.open(n):
            f = line.decode("latin-1").rstrip("\n").split("|")
            if len(f) > 28 and f[2] == "CA":
                rows.append([f[0], f[3], f[4].strip(), f[6].strip(), f[12].strip(), float(f[28])])
    json.dump(rows, open(cache, "w"))
    return rows

def sn(value, unit, note, url, low=None, high=None):
    d = {"value": value, "unit": unit, "method": "computed",
         "source": {"id": "usda_rma_col", "title": "USDA RMA Cause of Loss, Summary of Business (colsom, 2010-2024)", "url": url,
                    "accessed": "2026-11-14", "verified": True}, "note": note}
    if low is not None: d["low"], d["high"] = low, high
    return d

def main():
    rows = []
    for y in YEARS: rows += load_year(y)
    print(f"CA rows 2010-2024: {len(rows)}")
    for preset, specs in PROFILES.items():
        out = {"preset_id": preset, "years": [YEARS[0], YEARS[-1]], "file_url_template": f"{BASE}/colsom_YYYY.zip",
               "page_url": PAGE, "layout_url": LAYOUT,
               "grouping": {**GROUPS, "other": "all remaining causes (incl. cold/frost/freeze, wind, hail, insects, disease, ARPI/SCO/ECO etc.)"},
               "profiles": {}}
        crops = collections.defaultdict(list)
        for fips, cname, crop, pred in specs: crops[crop].append((fips, cname, pred))
        for crop, lst in crops.items():
            for scope, counties in [(f"{lst[0][1]} County", [lst[0]])] + ([("Kings+Tulare", lst)] if len(lst) > 1 else []):
                fset = {c[0] for c in counties}
                tot = collections.Counter(); by_year = collections.defaultdict(float); raw = collections.Counter(); names = set()
                for yr, fips, _, com, cause, ind in rows:
                    if fips in fset and any(p(com) for f, _, p in counties if f == fips) and ind:
                        g = group_of(cause); tot[g] += ind; raw[cause] += ind; by_year[int(yr)] += ind; names.add(com)
                T = sum(tot.values())
                if T <= 0:
                    out["profiles"][f"{scope}|{crop}"] = {"error": "no indemnity rows"}; continue
                url = f"{BASE}/colsom_2010.zip .. colsom_2024.zip"
                p = {"scope": scope, "crop": crop, "commodity_names_matched": sorted(names),
                     "total_indemnity_usd": T, "years_with_indemnity": sorted(by_year),
                     "indemnity_by_year_usd": {str(k): v for k, v in sorted(by_year.items())},
                     "shares": {f"share_{g}": sn(round(tot[g] / T, 4), "fraction of indemnity", f"{scope} {crop}, 2010-2024, summed over all insurance plans", f"{BASE}/colsom_YYYY.zip (2010-2024)")
                                for g in ["drought", "excess_moisture", "heat", "other"]},
                     "raw_cause_shares": {k: round(v / T, 4) for k, v in raw.most_common()},
                     "share_peril_unattributed": round(sum(v for k, v in raw.items() if k.startswith(("ARPI", "GRP"))) / T, 4),
                     "caveat": "Insurance history, not a forecast."}
                if crop == "alfalfa_forage":
                    p["caveat"] += " Alfalfa is insured in CA under Forage Production / Pasture,Rangeland,Forage (rainfall-index plan); matched names listed. Most forage indemnity is area-yield/index-plan (ARPI/SCO/GRP) with no peril attribution: see share_peril_unattributed; do NOT present the drought/moisture split as meaningful when that share is high."
                out["profiles"][f"{scope}|{crop}"] = p
        d = Path(__file__).resolve().parents[1] / "out" / preset; d.mkdir(parents=True, exist_ok=True)
        json.dump(out, open(d / "rma_profile.json", "w"), indent=1)
        for k, p in out["profiles"].items():
            if "shares" in p:
                print(preset, k, p["commodity_names_matched"], f"${p['total_indemnity_usd']:,.0f}", {s: v["value"] for s, v in p["shares"].items()}, "years", len(p["years_with_indemnity"]))
            else: print(preset, k, p)
if __name__ == "__main__": main()
