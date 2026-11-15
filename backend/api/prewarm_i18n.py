"""Warm the Spanish translation cache (data/cache/_i18n/es.json) by calling the main routes with ?lang=es.
Run: python prewarm_i18n.py [base_url]     (default http://127.0.0.1:8787; the server needs DEEPSEEK_API_KEY)
Prints per-route status and seconds, then totals. A 'partial' fallback means the 8 s budget ran out; the cache kept filling in the
background, so run it again to see the rest."""
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8787").rstrip("/")
FIELD_ROUTES = ["", "/strategies", "/this_week", "/nasa_now", "/insurance", "/stress", "/outlook", "/news", "/first_nations", "/salmon",
                "/calendar", "/validation", "/models", "/zones", "/nation", "/nation/drought_rotation", "/nation/groundwater",
                "/nation/land_season", "/nation/funding", "/nation/report.json"]
GLOBAL_ROUTES = ["/api/glossary", "/api/lands", "/api/reach", "/api/bc/news", "/api/bc/signal"]


def get(path, lang=True):
    url = BASE + path + (("&" if "?" in path else "?") + "lang=es" if lang else "")
    t = time.time()
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            body = r.read()
            return r.status, r.headers.get("X-Lang-Fallback", ""), time.time() - t, body
    except urllib.error.HTTPError as e:
        return e.code, "", time.time() - t, b""
    except Exception:  # noqa: BLE001
        return 0, "", time.time() - t, b""


def main():
    st, _, _, body = get("/api/locations", lang=False)
    if st != 200:
        sys.exit(f"cannot list locations from {BASE} (status {st})")
    ids = [i["id"] for i in json.loads(body)["items"]]
    paths = [f"/api/locations/{pid}{r}" for pid in ids for r in FIELD_ROUTES] + GLOBAL_ROUTES
    crops = set()
    for pid in ids:
        s, _, _, b = get(f"/api/locations/{pid}/strategies", lang=False)
        if s == 200:
            crops |= {x["crop_id"] for it in json.loads(b)["items"] for x in it.get("crops", []) if isinstance(x, dict) and "crop_id" in x}
    paths += [f"/api/crops/{c}" for c in sorted(crops)]
    t0 = time.time()
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda p: (p, *get(p)), paths))
    n = {"ok": 0, "partial": 0, "en": 0, "skip": 0}
    for p, s, fb, dt, _ in res:
        k = "skip" if s != 200 else (fb or "ok") if fb in ("", "partial", "en") else "ok"
        n[k] += 1
        if s == 200 and (dt > 2 or fb):
            print(f"{s} {dt:5.1f}s {fb or 'ok':7} {p}")
    print(f"{len(paths)} routes in {time.time() - t0:.0f}s: {n['ok']} fully Spanish, {n['partial']} partial, {n['en']} English (no key), {n['skip']} not 200 (404/422 = no data for that field)")


main()
