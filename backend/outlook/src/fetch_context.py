"""Snowpack (CDEC statewide SWE), Bulletin 120 status, CVP/SWP allocations (official pages) and storage-vs-allocation history."""
import re, subprocess, html as H
import pandas as pd, numpy as np
from common import *

SWE_URL = "https://cdec.water.ca.gov/reportapp/javareports?name=DLYSWEQ"
B120_URL = "https://cdec.water.ca.gov/reportapp/javareports?name=B120UP"
B120_PAGE = "https://cdec.water.ca.gov/snow/bulletin120/"
CVP_PDF = "https://www.usbr.gov/mp/cvo/vungvari/water_allocations_historical.pdf"
CVP_NEWS = {"initial_2026-02-26": "https://www.usbr.gov/newsroom/news-release/5289", "2026-03-24": "https://www.usbr.gov/newsroom/news-release/5305",
            "2026-05-19": "https://www.usbr.gov/newsroom/news-release/5338", "2026-08-11": "https://www.usbr.gov/newsroom/news-release/5386"}
SWP_URLS = {"initial": "https://water.ca.gov/News/News-Releases/2025/Dec-25/SWP-Allocation",
            "jan": "https://www.water.ca.gov/News/News-Releases/2026/Jan-2026/December-Storms-Improved-Flexibility-Allow-DWR-to-Increase-State-Water-Project-Allocation",
            "may": "https://water.ca.gov/News/News-Releases/2026/May-2026/State-Water-Project-Allocation-Increases-Heading-into-Summer-Months"}
ACWA = "https://www.acwa.com/news/dwr-boosts-swp-allocation-heading-into-summer/"
SWP_HIST = "https://water.ca.gov/-/media/DWR-Website/Web-Pages/Programs/State-Water-Project/Management/SWP-Water-Contractors/Files/Historical-SWP-allocations-1996-2024-112923.pdf"

def text(url):
    s = get(url).text
    s = re.sub(r"<(script|style).*?</\1>", "", s, flags=re.S); s = re.sub(r"<[^>]+>", "\n", s); s = H.unescape(s)
    return [l.strip() for l in s.splitlines() if l.strip()]

# Final (last published) south-of-Delta ag / Sacramento River Settlement Contractors % per year, transcribed from the Reclamation PDF
CVP = {2015: (0, 75), 2016: (5, 100), 2017: (100, 100), 2018: (50, 100), 2019: (75, 100), 2020: (20, 100), 2021: (0, 75), 2022: (0, 18), 2023: (100, 100), 2024: (50, 100), 2025: (55, 100), 2026: (31, 100)}

def snow(fetched):
    L = text(SWE_URL); i = L.index("Statewide Summary")
    seg = L[i:i + 14]; pairs = {}
    date = next(l for l in L if re.match(r"[A-Z][a-z]+ \d+, 20\d\d$", l))
    swe = float(re.search(r"([\d.]+)\"", seg[seg.index("Average snow water equivalent") + 1]).group(1))
    pct = float(re.search(r"([\d.]+)%", seg[seg.index("Percent of Normal for this date") + 1]).group(1))
    stn = int(seg[seg.index("Number of Stations Reporting") + 1])
    return {"report_date": date, "stations": stn,
            "swe_inches": sn(swe, "inches", SWE_URL, "CDEC statewide average snow water equivalent", fetched, True, note=f"report dated {date}"),
            "pct_of_normal_for_date": sn(pct, "percent", SWE_URL, "CDEC statewide snow water equivalent, percent of normal for this date", fetched, True,
                note="Reported as 0% in mid-November: the normal for this date is near zero (snow season has not started); not informative until Dec-Jan."),
            "url": SWE_URL}

def b120(fetched):
    L = text(B120_URL); line = next(l for l in L if l.startswith("UNIMPAIRED FLOW FOR"))
    gen = next(l for l in L if l.startswith("Report generated"))
    return {"status": "not yet published for WY2027", "latest_on_cdec_page": f"{line}; {gen}", "wy2026_final_update": True,
            "url_tried": B120_URL, "also_tried": B120_PAGE, "fetched_at": fetched, "verified": True,
            "note": "The CDEC Bulletin 120 update summary page still shows the May 2026 (WY2026) update. First WY2027 forecast expected in winter (plan: from February). Outlook, not a forecast."}

def allocations(fetched):
    pdf = get(CVP_PDF).content; p = RAW / "cvp_hist.pdf"; p.parent.mkdir(exist_ok=True); p.write_bytes(pdf)
    t = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True).stdout
    top = t[:t.index("Year", 100)]
    assert "27-Oct-2026" in top and "31%" in top, "CVP table layout changed; re-check"
    cvp = {"source_url": CVP_PDF, "fetched_at": fetched, "verified": True,
           "latest_update": "2026-10-27 (Reclamation table header)",
           "wy2026": {"sacramento_river_settlement_contractors": sn(100, "percent of contract supply", CVP_PDF, "CVP 2026 allocation, Settlement Contractors/Water Rights (Shasta non-critical)", fetched, True),
                      "north_of_delta_ag": sn(100, "percent of contract total", CVP_PDF, "CVP 2026 allocation, north-of-Delta agricultural contractors", fetched, True),
                      "south_of_delta_ag": sn(31, "percent of contract total", CVP_PDF, "CVP 2026 allocation, south-of-Delta agricultural contractors, as of 27 Oct 2026", fetched, True,
                          note="Steps: 15% (26 Feb), 20% (24 Mar), 25% (19 May), 28% (11 Aug), 31% (27 Oct 2026). Reclamation news releases: " + ", ".join(CVP_NEWS.values()))},
           "news_releases": CVP_NEWS, "wy2027_initial": {"status": "not yet announced", "note": "Reclamation's initial CVP allocation has come in late February in 2025 and 2026 (table header dates); none exists for 2027 yet.", "url_tried": CVP_PDF}}
    swp = {"verified": False, "note": "DWR pages (water.ca.gov) return HTTP 403 to automated fetches, so the figures below are read from ACWA's copy of the DWR release and from search summaries; open the DWR URLs to confirm.",
           "steps": [{"date": "2025-12-01", "percent": 10, "label": "initial", "url": SWP_URLS["initial"]}, {"date": "2026-01-29", "percent": 30, "url": SWP_URLS["jan"]},
                     {"date": "2026-05-15", "percent": 45, "url": SWP_URLS["may"], "read_from": ACWA}],
           "latest": sn(45, "percent of requested Table A", ACWA, "DWR State Water Project 2026 allocation (15 May 2026), via ACWA", fetched, False,
                        note="DWR 'final allocation typically near end of season'; no later change found. DWR release URL: " + SWP_URLS["may"]),
           "wy2027_initial": {"status": "not yet announced", "note": "DWR must issue an initial forecast by 1 December (as in 2025); not yet out on 14 Nov 2026.", "url_tried": SWP_URLS["initial"]},
           "history_blocked": {"url_tried": SWP_HIST, "why": "HTTP 403 to automated fetch; past SWP final allocations not sourced, so not used in the storage relation"}}
    return cvp, swp

def relation(fetched):
    h = pd.concat([pd.read_parquet(CACHE / "car_colusa_rice/cdec.parquet"), pd.read_parquet(CACHE / "car_colusa_rice/cdec_2026.parquet")])
    h["date"] = pd.to_datetime(h.date); sha = h[h.station == "SHA"].set_index("date").storage_af
    rows = []
    for Y in range(2016, 2027):
        v = sha.get(pd.Timestamp(Y - 1, 11, 13), np.nan)
        rows.append({"allocation_year": Y, "shasta_storage_13nov_prior_af": None if np.isnan(v) else float(v), "pct_of_capacity": None if np.isnan(v) else round(100 * float(v) / 4552000, 1),
                     "cvp_south_of_delta_ag_pct": CVP[Y][0], "cvp_settlement_contractors_pct": CVP[Y][1], "partial_year": Y == 2026})
    now_v = float(sha.get(pd.Timestamp(2026, 11, 13)))
    return {"method": "Shasta storage on 13 Nov before each allocation year (CDEC cache, 2015-2026) beside Reclamation's last published CVP allocation for that year. 11 years, descriptive only; the 2026 allocation may still change. SWP history not sourced (DWR 403).",
            "rows": rows, "shasta_13nov_2026_af": now_v, "unit": "acre-feet", "sources": [CVP_PDF, "data/cache/car_colusa_rice/cdec.parquet", "data/cache/car_colusa_rice/cdec_2026.parquet"], "fetched_at": fetched, "verified": True}

def main():
    f = now(); cvp, swp = allocations(f)
    out = {"fetched_at": f, "snow_now": snow(f), "bulletin_120": b120(f), "allocations": {"cvp": cvp, "swp": swp, "storage_vs_final_allocation": relation(f)}}
    write_json(OUT / "context.json", out)
    print(out["snow_now"]["swe_inches"]["value"], out["snow_now"]["pct_of_normal_for_date"]["value"], out["bulletin_120"]["latest_on_cdec_page"])
    for r in out["allocations"]["storage_vs_final_allocation"]["rows"]: print(r)

if __name__ == "__main__":
    main()
