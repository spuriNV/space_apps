"""PASS/FAIL checks for out/*.json. Run: uv run python checks/run_checks.py"""
import json, random, sys
from pathlib import Path
import httpx
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from news.windows import WINDOWS, OUTPUT

fails = 0
def rep(ok, msg):
    global fails
    fails += (not ok); print(("PASS " if ok else "FAIL ") + msg)

data = {p: json.loads((ROOT / "out" / f"{p}.json").read_text()) for p in OUTPUT}
allitems = [i for v in data.values() for i in v]
rep(all(i.get(k) for i in allitems for k in ("date", "title", "source", "url")), f"every item has date, title, source, url ({len(allitems)} items)")
rep(all(i["signal"]["lead_days"] is None for i in allitems), "signal.lead_days is null everywhere (not computed)")
bad = [i["title"] for i in allitems if not (WINDOWS[i["query_id"]]["start"] <= i["date"] <= WINDOWS[i["query_id"]]["end"])]
rep(not bad, f"dates inside their window {bad}")
keys = [(i["url"]) for i in allitems]; titles = [(i["query_id"], i["title"].lower()) for i in allitems]
rep(len(set(keys)) == len(keys) and len(set(titles)) == len(titles), "no duplicate urls or titles")
for p, wids in OUTPUT.items():
    for w in wids:
        n = sum(i["query_id"] == w for i in data[p])
        rep(n >= 1, f"window {w} has {n} item(s)")
ok = True
for p in data:
    for w in OUTPUT[p]:
        r = [i["rank"] for i in data[p] if i["query_id"] == w]
        ok &= r == sorted(r)
rep(ok, "ranking order holds (rank ascending within each window)")
rep(all(i["place_match"] for i in allitems), "every item has a place match")
random.seed(1)
sample = [i for i in allitems if i["_via"] != "google_news"][:3] + random.sample([i for i in allitems if i["_via"] == "google_news"], min(3, sum(i["_via"] == "google_news" for i in allitems)))
for i in sample:
    try:
        r = httpx.get(i["url"], headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, timeout=25)
        print(f"INFO HTTP {r.status_code} {i['url'][:90]}  final={str(r.url)[:70]}")
        rep(r.status_code < 400, f"url resolves: {i['title'][:50]}")
    except Exception as e:
        rep(False, f"url fetch error {type(e).__name__}: {e} for {i['url'][:80]}")
print("DONE", "all passed" if not fails else f"{fails} failed")
