"""PASS/FAIL checks for backend/outlook. Run: uv run python checks/run_checks.py"""
import json, sys, datetime as dt
from pathlib import Path
OUT = Path(__file__).resolve().parents[1] / "out"
TODAY = dt.date.today()
fails = 0
def chk(name, ok, detail=""):
    global fails
    print(("PASS" if ok else "FAIL"), name, detail)
    fails += 0 if ok else 1
def walk(o, path=""):
    if isinstance(o, dict):
        yield path, o
        for k, v in o.items(): yield from walk(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from walk(v, f"{path}[{i}]")
age = lambda d: (TODAY - dt.date.fromisoformat(str(d)[:10])).days
for pid in ("car_colusa_rice", "caf_tulare_forage"):
    f = OUT / pid / "outlook.json"
    if not f.exists(): chk(f"{pid} outlook.json exists", False); continue
    o = json.loads(f.read_text()); p = pid[:3]
    chk(f"{p} label outlook-not-forecast", "not a forecast" in o["label"].lower() and "not a forecast" in o["plain_language_summary"].lower())
    # dates
    dm = o["drought"]["us_drought_monitor"]; chk(f"{p} USDM map within 21 days", age(dm["map_date"]) <= 21, f"{dm['map_date']} ({age(dm['map_date'])} d)")
    for s, r in o["reservoirs_now"].items():
        chk(f"{p} CDEC {s} latest daily within 21 days", age(r["latest_daily_date"]) <= 21, r["latest_daily_date"])
        st, cap = r["storage_af"]["value"], r["capacity_af"]["value"]
        chk(f"{p} {s} storage within 0..capacity", 0 < st <= cap, f"{st:,.0f} / {cap:,.0f}")
        chk(f"{p} {s} % of average consistent (+/-1.5)", abs(100 * st / r["cdec_average_storage_af"]["value"] - r["pct_of_cdec_average"]["value"]) <= 1.5)
    sw = o["snowpack_runoff"]["snow_now_statewide"]; chk(f"{p} snow report within 21 days", age(dt.datetime.strptime(sw["report_date"], "%B %d, %Y").date()) <= 21, sw["report_date"])
    seas = o["cpc_seasonal_outlook"]["seasons"]; iss = seas[0]["temperature"]["issued"]
    chk(f"{p} CPC 90-day outlook issued within 35 days (monthly product)", age(iss) <= 35, iss)
    ds = o["drought"]["cpc_drought_outlook"]["seasonal"]["issued"]; chk(f"{p} CPC drought outlook within 35 days", age(dt.datetime.strptime(ds, "%m/%d/%Y").date()) <= 35, ds)
    chk(f"{p} CPC covers Dec-Feb and Jan-Mar", {"DJF", "JFM"} <= {s["season"] for s in seas})
    bad = [(s["season"], k) for s in seas for k in ("temperature", "precipitation") if s[k]["category"] != "equal chances" and not 33 <= s[k]["probability"]["value"] <= 100]
    chk(f"{p} CPC probabilities 33-100 where not equal chances", not bad, str(bad))
    # generic SourcedNumber rules
    badr, nosrc = [], []
    for path, d in walk(o):
        if "value" in d and isinstance(d["value"], (int, float)) and "unit" in d:
            if not (d.get("source", {}).get("url") and d.get("fetched_at") and "verified" in d): nosrc.append(path)
            lo, hi, v = d.get("low"), d.get("high"), d["value"]
            if (lo is not None and lo > v + 1e-9) or (hi is not None and hi < v - 1e-9): badr.append(path)
    chk(f"{p} every SourcedNumber has url, fetched_at, verified", not nosrc, str(nosrc[:3]))
    chk(f"{p} all low <= value <= high", not badr, str(badr[:3]))
    for s in o["irrigation_2027"]["strategies"]:
        i = s["irrigation_need_af_ac"]; chk(f"{p} irrigation {s['id']} low<=value<=high", i["low"] <= i["value"] <= i["high"], f"{i['low']} {i['value']} {i['high']}")
    n = len([x for x in o["plain_language_summary"].split(". ") if x.strip()]); chk(f"{p} plain summary 3-5 sentences", 3 <= n <= 5, str(n))
    chk(f"{p} blocked/not-yet-published listed with URLs", all(b.get("url_tried") for b in o["blocked_or_not_yet_published"]))
print("\nRESULT:", "ALL PASS" if not fails else f"{fails} FAIL"); sys.exit(1 if fails else 0)
