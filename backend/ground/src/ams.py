"""AMS MARS California hay. GET https://marsapi.ams.usda.gov/services/v1.2/reports/{slug}?allSections=true&q=report_begin_date=... ; HTTP Basic, key as username, empty password.
Slug 2904 = California Direct Hay Report (U: from search summaries; run with a key and check out/ams_reports.json)."""
import json, requests, pandas as pd
from common import *
BASE = "https://marsapi.ams.usda.gov/services/v1.2/reports"
SLUGS = [2904]
def main():
    key = need_key("AMS_API_KEY")
    (GROUND / "out").mkdir(exist_ok=True)
    r = requests.get(BASE, auth=(key, ""), timeout=120)
    if r.status_code == 200: json.dump(r.json(), open(GROUND / "out" / "ams_reports.json", "w"))
    else: print(f"report list HTTP {r.status_code}")
    frames = []
    for s in SLUGS:
        for y in range(2015, 2026):
            r = requests.get(f"{BASE}/{s}", params={"allSections": "true", "q": f"report_begin_date=01/01/{y}:12/31/{y}"}, auth=(key, ""), timeout=180)
            if r.status_code != 200: print(f"slug {s} {y}: HTTP {r.status_code} {r.text[:150]}"); continue
            js = r.json(); secs = js if isinstance(js, list) else [js]
            for sec in secs:
                rows = sec.get("results", []) if isinstance(sec, dict) else []
                if rows: frames.append(pd.json_normalize(rows).assign(slug=s, report_section=sec.get("reportSection", "")))
    if not frames: print("AMS: no rows returned"); return
    df = pd.concat(frames, ignore_index=True)
    for p in PRESETS:
        meta, path = write_cache(p, "ams", df.astype(str), BASE, {"slugs": SLUGS, "years": "2015-2025"})
        save_meta(meta, path, verified=True); print(f"{p}: {len(df)} rows -> ams.parquet")
if __name__ == "__main__": main()
