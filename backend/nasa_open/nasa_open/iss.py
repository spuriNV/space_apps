"""ISS astronaut photos (NASA JSC Gateway to Astronaut Photography of Earth, eol.jsc.nasa.gov, no login).
Photos were chosen from cataloged-with-centre-point search results (see out/iss_search/*.tsv); metadata is read from each photo's page.
Usage: uv run python -m nasa_open.iss"""
import re, time, requests
from .common import *
CREDIT = "Image courtesy of the Earth Science and Remote Sensing Unit, NASA Johnson Space Center"
PICKS = {"car_colusa_rice": ["ISS062-E-81144", "ISS062-E-81143", "ISS062-E-81142"],
         "caf_tulare_forage": ["ISS062-E-75297", "ISS062-E-75293", "ISS062-E-75296"]}
BASE = "https://eol.jsc.nasa.gov"

def get(url, **kw):
    for i in range(5):
        try:
            r = requests.get(url, timeout=180, **kw); r.raise_for_status(); return r
        except Exception as e:
            err = e; time.sleep(5 * (i + 1))
    raise err

def meta(pid):
    m, r, f = pid.split("-")
    html = get(f"{BASE}/SearchPhotos/photo.pl", params={"mission": m, "roll": r, "frame": f}).text
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)))
    g = lambda pat: (re.search(pat, t) or [None, None])[1]
    d = g(r"Date taken (\d{4}\.\d\d\.\d\d)")
    c = re.search(r"Photo center point: ([\d.]+)\S* ([NS]), ([\d.]+)\S* ([EW])", t)
    lat = float(c[1]) * (1 if c[2] == "N" else -1); lon = float(c[3]) * (1 if c[4] == "E" else -1)
    return {"photo_id": pid, "mission": m, "roll": r, "frame": f, "date": d.replace(".", "-"), "time_gmt": g(r"Time taken ([\d:]+) GMT"),
            "center_lat": lat, "center_lon": lon, "lens_mm": int(g(r"Focal Length: (\d+)mm")), "camera": g(r"Camera: (.+?) Focal Length"),
            "cloud_pct_class": g(r"Cloud Cover Percentage: (\S+)"), "tilt_deg": g(r"Camera Tilt: (\S+)"), "features": g(r"Features: (.+?) Features Found"),
            "altitude_km": g(r"Spacecraft Altitude : \d+ nautical miles \((\d+)km\)"),
            "page_url": f"{BASE}/SearchPhotos/photo.pl?mission={m}&roll={r}&frame={f}",
            "image_url": f"{BASE}/DatabaseImages/ESC/large/{m}/{pid}.JPG", "thumb_url": f"{BASE}/DatabaseImages/ESC/small/{m}/{pid}.JPG",
            "credit": CREDIT}

if __name__ == "__main__":
    for p, ids in PICKS.items():
        d = CACHE / p / "iss"; d.mkdir(parents=True, exist_ok=True); photos = []
        for pid in ids:
            x = meta(pid); r = get(x["image_url"])
            (d / f"{pid}.jpg").write_bytes(r.content); x["local_file"] = f"data/cache/{p}/iss/{pid}.jpg"; x["bytes"] = len(r.content)
            photos.append(x); print(p, pid, x["date"], x["center_lat"], x["center_lon"], x["lens_mm"], x["bytes"])
        write_json(d / "iss.json", {"preset_id": p, "fetched_at": now(), "source": "https://eol.jsc.nasa.gov/SearchPhotos/", "credit": CREDIT,
                                    "note": "Cataloged photos with a centre point inside the search box; centre points are stored to 0.1 degree.", "photos": photos})
