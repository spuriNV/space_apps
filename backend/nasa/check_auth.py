"""Log in with .env credentials and report per-DAAC access PASS/FAIL with the fix.
Run: uv run python check_auth.py"""
import os
import sys

import requests

from fieldshift_nasa import common as C

if not C.load_env():
    print(C.BLOCKED_MSG)
    sys.exit(0)

import earthaccess

APP_FIX = ("Fix: https://urs.earthdata.nasa.gov -> Applications -> Authorized Apps -> Approve More Applications, "
           "approve {app} (name may differ slightly; approve the closest match), then re-run.")
# (label, CMR collection concept id, approval to look for)
DAACS = [
    ("GES DISC (IMERG, GRACE-DA)", "C2723754864-GES_DISC", "'NASA GESDISC DATA ARCHIVE'"),
    ("NSIDC (SMAP L3/L4)", "C2938664763-NSIDC_CPRD", "the NSIDC DAAC application ('NSIDC_DATAPOOL_OPS' / 'NSIDC DAAC Data Pool' / 'NSIDC_ECS')"),
    ("LP DAAC (MODIS, ECOSTRESS)", "C1748066515-LPCLOUD", "'LP DAAC Data Pool'"),
    ("PO.DAAC (OPERA DSWx)", "C2617126679-POCLOUD", "'PO.DAAC Data Website' / 'PODAAC' (and 'Earthdata Cloud' if listed)"),
]
fails = 0
try:
    auth = earthaccess.login(strategy="environment")
    ok = bool(auth and auth.authenticated)
except Exception as e:  # noqa: BLE001
    ok, err = False, f"{type(e).__name__}: {str(e)[:200]}"
if not ok:
    print("FAIL Earthdata Login (URS): could not log in. Fix: check EARTHDATA_USERNAME/PASSWORD in .env "
          "(note: URS password, not email) and that the account email is confirmed.")
    sys.exit(1)
print("PASS Earthdata Login (URS)")
sess = earthaccess.get_requests_https_session()
for label, cid, app in DAACS:
    try:
        r = requests.get("https://cmr.earthdata.nasa.gov/search/granules.json",
                         params={"collection_concept_id": cid, "page_size": 1}, timeout=60).json()
        g = r["feed"]["entry"][0]
        urls = [l["href"] for l in g["links"] if l["rel"].endswith("/data#") and l["href"].startswith("https")
                and not l["href"].endswith((".md5", ".xml", ".png", ".json", ".pdf"))]
        url = urls[0]
        resp = sess.get(url, headers={"Range": "bytes=0-1023"}, timeout=90, allow_redirects=True)
        body = resp.text[:200].replace("\n", " ") if resp.status_code >= 300 or "html" in resp.headers.get("content-type", "") else ""
        if resp.status_code in (200, 206) and not body:
            print(f"PASS {label}: HTTP {resp.status_code} on {url.split('/')[-1][:60]}")
        else:
            fails += 1
            print(f"FAIL {label}: HTTP {resp.status_code} {body or resp.headers.get('content-type')} ({url[:90]})\n     " + APP_FIX.format(app=app))
    except Exception as e:  # noqa: BLE001
        fails += 1
        print(f"FAIL {label}: {type(e).__name__}: {str(e)[:200]}\n     " + APP_FIX.format(app=app))
try:
    ae = C.AppEEARS()
    r = requests.get(f"{C.APPEEARS}/status", headers=ae.h, timeout=60)
    print(f"PASS LP DAAC / AppEEARS API: token issued (status endpoint HTTP {r.status_code})")
except Exception as e:  # noqa: BLE001
    fails += 1
    print(f"FAIL AppEEARS API: {str(e)[:300]}")
print("ALL PASS" if not fails else f"{fails} FAIL(s): fetchers for the failing DAAC will not work until fixed")
sys.exit(1 if fails else 0)
