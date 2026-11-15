"""GET /api/locations/bc_salmon_river_forage/salmon: "Salmon and the field". No network.

Run (backend/api venv: pandas + the rotation engine):
    cd backend/api && uv run python ../bc/salmon.py
Inputs (fetch first; both no key):
    data/cache/bc_salmon_river_forage/wsc_daily.parquet, wsc.meta.json    <- backend/bc/fetch_wsc.py  (WSC 08LE021, 08LE020)
    data/cache/bc_salmon_river_forage/modis_snow.parquet, .meta.json      <- backend/bc/fetch_snow.py (MOD10A2, FWA group SALR)
    data/cache/bc_salmon_river_forage/{imerg,grace,eccc}.parquet          (backend/nasa, backend/bc/fetch_eccc.py)
    backend/engine strategies (monthly irrigation need recomputed with the engine's own timeline and water balance)
Writes backend/api/out/bc_salmon_river_forage/salmon.json (schema schemas/salmon.schema.json).

Every number is a SourcedNumber {value, unit, method, source{id,title,url,accessed,verified}, note?}.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FID = "bc_salmon_river_forage"
CACHE = REPO / "data" / "cache" / FID
OUT = REPO / "backend" / "api" / "out" / FID
TODAY = "2026-11-15"
GAUGE = "08LE021"
UPPER = "08LE020"
REF = (1991, 2020)            # reference period for percentiles and MAD
FIELD_HA = 21.51

os.environ["FIELDSHIFT_FIELDS"] = ",".join(sorted({*filter(None, os.environ.get("FIELDSHIFT_FIELDS", "").split(",")), FID}))
sys.path.insert(0, str(REPO / "backend" / "fields"))


# ------------------------------------------------------------------ sources (every URL opened on 2026-11-15)
def S(id_, title, url, verified=True, accessed=TODAY):
    return {"id": id_, "title": title, "url": url, "accessed": accessed, "verified": verified}


SRC = {
    "hydat": S("wsc_hydat_08LE021", "Water Survey of Canada, HYDAT daily mean discharge, 08LE021 Salmon River near Salmon Arm",
               "https://wateroffice.ec.gc.ca/report/historical_e.html?stn=08LE021"),
    "hydat_up": S("wsc_hydat_08LE020", "Water Survey of Canada, HYDAT daily mean discharge, 08LE020 Salmon River at Falkland",
                  "https://wateroffice.ec.gc.ca/report/historical_e.html?stn=08LE020"),
    "rt": S("wsc_realtime_08LE021", "Water Survey of Canada real-time hydrometric data (provisional), 08LE021",
            "https://wateroffice.ec.gc.ca/report/real_time_e.html?stn=08LE021"),
    "rt_up": S("wsc_realtime_08LE020", "Water Survey of Canada real-time hydrometric data (provisional), 08LE020",
               "https://wateroffice.ec.gc.ca/report/real_time_e.html?stn=08LE020"),
    "m311": S("bc_order_m311_2026", "BC Ministerial Order M311 (2026), fish population protection order, Water Sustainability Act s.88",
              "https://news.gov.bc.ca/files/MinisterialOrderM311.pdf"),
    "m238": S("bc_order_m238_2023", "BC Ministerial Order M238 (2023), fish population protection order, lower Salmon River",
              "https://www.bclaws.gov.bc.ca/civix/document/id/mo/hmo/m0238_2023"),
    "m328": S("bc_order_m328_2021", "BC Ministerial Order M328 (2021), fish population protection order, Salmon River",
              "https://www.bclaws.gov.bc.ca/civix/document/id/mo/hmo/m0328_2021"),
    "drought_plan": S("bc_fisheries_drought_plan_2025", "BC Provincial Fisheries Management Drought Response Plan (July 2025)",
                      "https://www2.gov.bc.ca/assets/gov/sports-recreation-arts-and-culture/outdoor-recreation/fishing-and-hunting/freshwater-fishing/provincial_fisheries_management_drought_response_plan.pdf"),
    "bc_wqg_temp": S("bc_wqg_temperature_2001", "BC Water Quality Guidelines for Temperature, Overview Report (Oliver & Fidler, 2001)",
                     "https://www2.gov.bc.ca/assets/gov/environment/air-land-water/water/waterquality/water-quality-guidelines/approved-wqgs/temperature-or.pdf"),
    "dfo_frw": S("dfo_fraser_env_watch_2026_09_14", "DFO Fraser River Environmental Watch report, 14 Sep 2026 (temperature effects on migrating sockeye)",
                 "https://www.pac.dfo-mpo.gc.ca/science/habitat/frw-rfo/reports-rapports/2026/2026-09-14-eng.html"),
    "cosewic": S("cosewic_chinook_2020", "COSEWIC assessment and status report, Chinook Salmon (2020): DU13 South Thompson Stream Summer 1.3",
                 "https://www.canada.ca/en/environment-climate-change/services/species-risk-public-registry/cosewic-assessments-status-reports/chinook-salmon-2020.html"),
    "sa_observer": S("sa_observer_2015_chinook", "Salmon Arm Observer, \"Chinook numbers down\" (6 Nov 2015; counting-fence results)",
                     "https://www.saobserver.net/community/chinook-numbers-down/"),
    "work_windows": S("bc_work_windows_salmon_arm", "BC Ministry of Environment, Salmon Arm Forest District instream work windows (2005)",
                      "https://www.env.gov.bc.ca/thompson/documents/work_windows/salmon_arm.pdf"),
    "bc_2026": S("bc_news_2026_salmon_river", "BC Government news release 2026WLRS0042-000965 (Salmon River temporary protection order)",
                 "https://news.gov.bc.ca/releases/2026WLRS0042-000965"),
    "bc_2023": S("bc_news_2023_salmon_river", "BC Government news release 2023FOR0052-001305 (fish population protection orders)",
                 "https://news.gov.bc.ca/releases/2023FOR0052-001305"),
    "psf": S("psf_drought_monitoring", "Pacific Salmon Foundation, \"Smarter drought monitoring for salmon\"",
             "https://psf.ca/blog/smarter-drought-monitoring-for-salmon/"),
    "modis": S("nasa_mod10a2_061", "NASA MODIS/Terra Snow Cover 8-Day L3 Global 500 m (MOD10A2 v061), Planetary Computer COGs",
               "https://doi.org/10.5067/MODIS/MOD10A2.061"),
    "imerg": S("nasa_gpm_imerg", "NASA GPM IMERG daily precipitation v07 (Final; Late after Sep 2025)", "https://doi.org/10.5067/GPM/IMERGDF/DAY/07"),
    "grace": S("nasa_grace_da", "NASA GRACE-DA (GRACEDADM_CLSM025GL_7D v3.0) root-zone soil moisture percentile",
               "https://disc.gsfc.nasa.gov/datasets/GRACEDADM_CLSM025GL_7D_3.0/summary"),
    "eccc": S("eccc_climate_daily", "Environment and Climate Change Canada daily climate data, Salmon Arm CS (116FRMN)",
              "https://api.weather.gc.ca/collections/climate-daily"),
    "fwa": S("bc_fwa_watershed_groups", "BC Freshwater Atlas watershed groups (WHSE_BASEMAPPING.FWA_WATERSHED_GROUPS_POLY), group SALR",
             "https://catalogue.data.gov.bc.ca/dataset/freshwater-atlas-watershed-groups"),
    "engine": S("fieldshift_engine_irrigation", "CropLytics rotation engine: monthly irrigation need max(0, ETc - 0.8 P) per irrigated crop (FAO-56 ETc)",
                "https://www.fao.org/3/x0490e/x0490e00.htm", verified=False),
    "assumed": S("assumed", "Team assumption (stated in the note); not from a cited source", "urn:fieldshift:assumed", verified=False),
    "registry": S("field_registry", "CropLytics field outline (ParcelMap BC parcel x AAFC ACI forage pixels)", "https://ltsa.ca/products-services/parcelmap-bc/"),
    "splatsin": S("splatsin_land", "Splatsin, Your Government: Land", "https://splatsin.ca/your-government/land"),
}


def r(x, nd=3):
    if x is None:
        return None
    try:
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return None
        if pd.isna(x):
            return None
    except (TypeError, ValueError):
        pass
    return round(float(x), nd)


def sn(value, unit, method, source, note=None, low=None, high=None, nd=3, **extra):
    d = {"value": r(value, nd), "unit": unit, "method": method}
    if low is not None or high is not None:
        d["low"], d["high"] = r(low, nd), r(high, nd)
    if d["value"] is not None or source:
        d["source"] = source
    if note:
        d["note"] = note
    d.update(extra)
    return d


def jload(p):
    return json.loads(Path(p).read_text())


def km(a_lat, a_lon, b_lat, b_lon):
    p1, l1, p2, l2 = map(np.radians, (a_lat, a_lon, b_lat, b_lon))
    h = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin((l2 - l1) / 2) ** 2
    return float(6371 * 2 * np.arcsin(np.sqrt(h)))


# ------------------------------------------------------------------ inputs
def load_wsc():
    d = pd.read_parquet(CACHE / "wsc_daily.parquet")
    d["date"] = pd.to_datetime(d.date)
    return d, jload(CACHE / "wsc.meta.json")


def series(d, stn, col="discharge_m3s"):
    g = d[d.station == stn].set_index("date").sort_index()
    return g[col].dropna(), g


def doy365(idx):
    """Day of year on a 365-day calendar (29 Feb folded onto 28 Feb)."""
    doy = idx.day_of_year.values.copy()
    leap = idx.is_leap_year & (idx.month > 2)
    doy[leap] -= 1
    doy[(idx.month == 2) & (idx.day == 29)] = 59
    return doy


def doy_percentiles(q):
    ref = q[(q.index.year >= REF[0]) & (q.index.year <= REF[1])]
    doy = doy365(ref.index)
    vals = ref.values
    out = []
    for k in range(1, 366):
        dist = np.minimum(np.abs(doy - k), 365 - np.abs(doy - k))
        v = vals[dist <= 7]
        out.append({"doy": k, "date_label": (dt.date(2025, 1, 1) + dt.timedelta(days=k - 1)).strftime("%m-%d"),
                    **{f"p{p}": r(np.percentile(v, p), 3) for p in (10, 25, 50, 75, 90)}, "n": int(len(v))})
    return out, ref, doy


def pct_rank(value, ref_vals):
    v = np.asarray(ref_vals)
    v = v[~np.isnan(v)]
    if not len(v) or value is None:
        return None
    return float(100 * ((v < value).sum() + 0.5 * (v == value).sum()) / len(v))


# ------------------------------------------------------------------ 1. river flow
def build_flow(d, meta):
    q, g = series(d, GAUGE)
    qu, _ = series(d, UPPER)
    pct, ref, ref_doy = doy_percentiles(q)
    info = meta["stations"][GAUGE]
    src_q = SRC["hydat"]

    # long-term mean annual discharge (MAD) over complete reference years
    ry = ref.groupby(ref.index.year)
    full = [y for y, s in ry if len(s) >= 360]
    mad = float(ref[ref.index.year.isin(full)].mean())
    aug = q[q.index.month == 8]
    aug_ref = aug[(aug.index.year >= REF[0]) & (aug.index.year <= REF[1])]
    p10_aug = float(np.percentile(aug_ref, 10))

    mad_note = (f"Long-term mean annual discharge (LT MAD) of 08LE021 over the complete years {REF[0]}-{REF[1]} "
                f"({len(full)} years, HYDAT approved daily means), computed by us. BC's drought plan uses % of LT MAD; "
                "BC has not published this station's MAD in a page we could open.")
    thresholds = [
        {"id": "order_2026_m311", "kind": "official", "label": "2026 order trigger (M311): flow dropped below 0.625 m³/s",
         "value": sn(0.625, "m3/s", "lookup", SRC["m311"],
                     "Order M311 (signed 19 Aug 2026, in effect to 30 Sep 2026): \"the flow of water in the Salmon River has dropped "
                     "below 0.625 cubic metres per second and is so low that the survival of the Chinook salmon fish population in "
                     "the stream has become threatened\". The order names no gauge; we draw it against 08LE021."),
         "applies": {"from": "2026-08-19", "to": "2026-09-30"}},
        {"id": "order_2023_m238", "kind": "official", "label": "2023 order trigger (M238): flow dropped below 1.27 m³/s",
         "value": sn(1.27, "m3/s", "lookup", SRC["m238"],
                     "Order M238 (15 Aug to 30 Sep 2023, lower Salmon River east of Westwold): flow \"dropped below 1.27 cubic "
                     "metres per second\" (Thompson River Chinook). The 2021 order M328 used the same value, 1,270 L/s. No gauge named."),
         "applies": {"from": "2023-08-15", "to": "2023-09-30"}},
        {"id": "mad_20pct", "kind": "policy_rule", "label": "20% of long-term mean annual flow (adult salmon passage)",
         "value": sn(0.20 * mad, "m3/s", "computed", SRC["drought_plan"],
                     "BC drought plan (2025): \"adult salmon/char passage flows (>20% LT MAD) required prior to spawning\". 20% x "
                     f"our computed LT MAD {mad:.2f} m³/s."), "applies": None},
        {"id": "mad_10pct", "kind": "policy_rule", "label": "10% of long-term mean annual flow (acute concern)",
         "value": sn(0.10 * mad, "m3/s", "computed", SRC["drought_plan"],
                     "BC drought plan (2025): \"Flows that drop to or below 10%LT MAD are of acute fisheries concern\". "
                     f"10% x our LT MAD {mad:.2f} m³/s."), "applies": None},
        {"id": "mad_5pct", "kind": "policy_rule", "label": "5% of long-term mean annual flow (severe impacts; \"critical environmental flows\")",
         "value": sn(0.05 * mad, "m3/s", "computed", SRC["drought_plan"],
                     "BC drought plan (2025): \"Stream flows below 5% LT MAD represent flows that can have severe impacts on fish "
                     "populations\" (the 2019 plan calls this \"critical environmental flows\"). No Salmon River CEFT number is "
                     f"published. 5% x our LT MAD {mad:.2f} m³/s."), "applies": None},
        {"id": "aug_p10_reference", "kind": "our_reference", "label": "Our reference: 10th percentile of August daily flow",
         "value": sn(p10_aug, "m3/s", "computed", src_q,
                     f"10th percentile of all August daily means at 08LE021, {REF[0]}-{REF[1]}. Our reference for a 'typical low "
                     "August flow', not an official threshold."), "applies": None},
    ]

    # latest real-time reading
    lt = info.get("latest_realtime") or {}
    latest = None
    if lt.get("discharge_m3s") is not None:
        ts = pd.Timestamp(lt["datetime_local"])
        k = int(doy365(pd.DatetimeIndex([ts.tz_localize(None)]))[0])
        dist = np.minimum(np.abs(ref_doy - k), 365 - np.abs(ref_doy - k))
        latest = {"datetime_utc": lt["datetime_utc"], "datetime_local": lt["datetime_local"],
                  "discharge": sn(lt["discharge_m3s"], "m3/s", "measured", SRC["rt"], "Provisional real-time reading (5-minute), subject to revision."),
                  "level": sn(lt["level_m"], "m", "measured", SRC["rt"], "Water level on the station's assumed datum (not elevation)."),
                  "percentile_for_date": sn(pct_rank(lt["discharge_m3s"], ref.values[dist <= 7]), "percentile", "computed", src_q,
                                            f"Where this reading sits among {REF[0]}-{REF[1]} daily means within +/-7 days of the same date (0 = lowest)."),
                  "pct_of_mad": sn(100 * lt["discharge_m3s"] / mad, "% of LT MAD", "computed", src_q)}

    # daily history (2015 on, like daily.json), with approval and the percentile band for that day
    q15 = g.loc["2015-01-01":, ["discharge_m3s", "approval"]].dropna(subset=["discharge_m3s"])
    pmap = {p["doy"]: p for p in pct}
    dd = doy365(q15.index)
    daily = [{"date": i.strftime("%Y-%m-%d"), "discharge_m3s": r(v.discharge_m3s, 3), "approval": v.approval,
              "p10": pmap[k]["p10"], "p50": pmap[k]["p50"]} for (i, v), k in zip(q15.iterrows(), dd)]

    # Aug-Sep of the order years
    orders = (jload(REPO / "backend/fields/registry.json")["fields_other_regions"][0]["water_context"]["orders"])
    order_years = []
    for y in (2023, 2026):
        w = q[f"{y}-07-15":f"{y}-09-30"]
        a = q[f"{y}-08-01":f"{y}-08-31"]
        s_ = q[f"{y}-08-01":f"{y}-09-30"]
        trig = next(t for t in thresholds if t["id"] == ("order_2023_m238" if y == 2023 else "order_2026_m311"))["value"]["value"]
        prov = bool((g.loc[f"{y}-08-01":f"{y}-09-30", "approval"] == "provisional").any())
        srcy = SRC["rt"] if prov else src_q
        order_years.append({
            "year": y,
            "orders": [o for o in orders if o["date"].startswith(str(y))],
            "data_status": "provisional" if prov else "approved",
            "daily": [{"date": i.strftime("%Y-%m-%d"), "discharge_m3s": r(v, 3),
                       "p10": pmap[int(k)]["p10"], "p50": pmap[int(k)]["p50"]} for (i, v), k in zip(w.items(), doy365(w.index))],
            "aug_mean": sn(a.mean(), "m3/s", "measured", srcy, f"Mean of August {y} daily means at 08LE021."),
            "aug_mean_pct_of_normal": sn(100 * a.mean() / float(aug_ref.median()), "% of median August flow", "computed", srcy,
                                         f"August {y} mean / median August daily flow {REF[0]}-{REF[1]} ({aug_ref.median():.2f} m³/s)."),
            "aug_sep_min": sn(s_.min(), "m3/s", "measured", srcy, f"Lowest daily mean 1 Aug-30 Sep {y} (on {s_.idxmin().date()})."),
            "days_below_order_trigger_aug_sep": sn(int((s_ < trig).sum()), "days", "computed", srcy,
                                                    f"Days 1 Aug-30 Sep {y} with daily mean below {trig} m³/s (that year's order value) at 08LE021."),
            "days_below_mad_10pct_aug_sep": sn(int((s_ < 0.10 * mad).sum()), "days", "computed", srcy,
                                               f"Days below 10% LT MAD ({0.10 * mad:.2f} m³/s)."),
            "aug_rank_lowest": sn(int((aug.groupby(aug.index.year).mean() <= a.mean()).sum()), "rank (1 = driest August)", "computed", srcy,
                                  f"Rank of August {y} mean flow among {aug.index.year.nunique()} Augusts on record at 08LE021 (1 = lowest)."),
        })

    aug_by_year = aug.groupby(aug.index.year).agg(["mean", "min", "size"])
    aug_by_year = aug_by_year[aug_by_year["size"] >= 28]
    upper_aug = qu[qu.index.month == 8].groupby(qu[qu.index.month == 8].index.year).mean()
    return {
        "station": GAUGE,
        "reference_period": list(REF),
        "mad": sn(mad, "m3/s", "computed", src_q, mad_note),
        "latest": latest,
        "thresholds": thresholds,
        "threshold_note": ("The only official numbers are the order triggers (0.625 m³/s in 2026, 1.27 m³/s in 2023 and 2021); the "
                           "orders say 'in the Salmon River' and name no gauge, so the 08LE021 line is our reading. BC publishes no "
                           "critical environmental flow threshold (CEFT) number for this river; the % MAD lines apply the BC drought "
                           "plan's rule to our computed MAD."),
        "percentiles_by_doy": pct,
        "daily": daily,
        "order_years": order_years,
        "aug_mean_by_year": [{"year": int(y), "aug_mean_m3s": r(v["mean"], 3), "aug_min_m3s": r(v["min"], 3),
                              "upper_falkland_aug_mean_m3s": r(upper_aug.get(y), 3)} for y, v in aug_by_year.iterrows()],
        "aug_mean_by_year_source": src_q,
    }, mad, p10_aug, aug_by_year["mean"]


# ------------------------------------------------------------------ 2. water temperature
TEMP_THRESHOLDS = [
    {"id": "t18", "label": "18 °C: salmon swim less well; BC guideline (weekly mean of daily max) for streams",
     "value": sn(18.0, "degC", "lookup", SRC["dfo_frw"],
                 "DFO Fraser River Environmental Watch (2026): \"18°C - Decreased swimming performance\". The BC Water Quality "
                 "Guideline for temperature (2001) sets MWMT (mean weekly maximum temperature) = 18 °C for streams where fish "
                 "distribution is unknown, and Chinook migration's optimum range tops out at 19.0 °C (Table 2)."),
     "also": [SRC["bc_wqg_temp"]]},
    {"id": "t20", "label": "20 °C: high pre-spawn mortality and disease; BC angling-closure trigger (MWMT > 20 °C)",
     "value": sn(20.0, "degC", "lookup", SRC["dfo_frw"],
                 "DFO Fraser River Environmental Watch (2026): \"20°C - Associated with high pre-spawn mortality and disease\". "
                 "BC drought plan (2025): angling measures \"where MWMT exceeds 20oC and/or maximum daily temperatures exceed 23oC\"."),
     "also": [SRC["drought_plan"]]},
]


def build_temperature(d, meta):
    out = {"thresholds": TEMP_THRESHOLDS, "stations": [], "satellite": None}
    for stn, src in ((GAUGE, SRC["rt"]), (UPPER, SRC["rt_up"])):
        g = d[d.station == stn].set_index("date").sort_index()
        t = g[["water_temp_c", "water_temp_max_c"]].dropna()
        if t.empty:
            continue
        mwmt = t.water_temp_max_c.rolling(7, min_periods=6).mean()
        summers = []
        for y in sorted(set(t.index.year)):
            s = t[f"{y}-06-01":f"{y}-09-30"]
            if len(s) < 60:
                continue
            m = mwmt[f"{y}-06-01":f"{y}-09-30"]
            summers.append({
                "year": y, "days_with_data": int(len(s)),
                "days_max_ge_18": sn(int((s.water_temp_max_c >= 18).sum()), "days", "computed", src,
                                     f"Days 1 Jun-30 Sep {y} with an hourly reading >= 18 °C."),
                "days_max_ge_20": sn(int((s.water_temp_max_c >= 20).sum()), "days", "computed", src,
                                     f"Days 1 Jun-30 Sep {y} with an hourly reading >= 20 °C."),
                "max_mwmt": sn(m.max(), "degC", "computed", src,
                               f"Highest 7-day mean of daily maximum (MWMT), the BC guideline's statistic; week ending {m.idxmax().date()}."),
                "peak": sn(s.water_temp_max_c.max(), "degC", "measured", src, f"Highest hourly reading, {s.water_temp_max_c.idxmax().date()}."),
            })
        info = meta["stations"][stn]
        out["stations"].append({
            "station": stn, "name": info["name"].title(), "role": info["role"],
            "first": str(t.index.min().date()), "last": str(t.index.max().date()),
            "daily": [{"date": i.strftime("%Y-%m-%d"), "mean_c": r(v.water_temp_c, 2), "max_c": r(v.water_temp_max_c, 2),
                       "mwmt_c": r(mwmt.get(i), 2)} for i, v in t.iterrows()],
            "summers": summers, "source": src,
            "note": "Provisional real-time water temperature (WSC parameter 5), hourly, averaged to UTC days. WSC keeps about 18 "
                    "months online, so there is no gauge temperature for 2023.",
        })
    out["satellite"] = {"status": "not_used",
                        "reason": "The gauges publish water temperature, which beats any satellite value here: the lower Salmon "
                                  "River is roughly 10-30 m wide, narrower than a Landsat thermal pixel (100 m, resampled to 30 m) "
                                  "or an ECOSTRESS pixel (70 m), so a river-pixel 'surface temperature' would mostly measure the "
                                  "warm banks and hay fields in summer."}
    return out


# ------------------------------------------------------------------ 3. run timing (+ irrigation overlay)
def run_timing(irr_months):
    months = list(range(1, 13))
    species = [
        {"species": "chinook", "common": "Chinook (South Thompson summer run, DU13)", "stage": "adults enter and hold",
         "months": [8, 9], "scope": "salmon_river",
         "evidence": "BC 2026 release: \"more than 200 adult Chinook salmon in the watershed\" by 19 Aug 2026; BC work windows list "
                     "Chinook arriving after the late-July window.", "sources": [SRC["bc_2026"], SRC["work_windows"]], "verified": True},
        {"species": "chinook", "common": "Chinook", "stage": "spawning", "months": [9, 10], "scope": "salmon_river",
         "evidence": "Counting-fence report: \"the chinook run peaks between Sept. 10 and 15\"; over by early November.",
         "sources": [SRC["sa_observer"]], "verified": True},
        {"species": "chinook", "common": "Chinook", "stage": "eggs in gravel, then juveniles rear one year in fresh water",
         "months": months, "scope": "salmon_river",
         "evidence": "COSEWIC 2020: DU13 spawns in Shuswap tributaries \"such as the Seymour, Eagle, Scotch and the Salmon rivers\"; "
                     "\"the juveniles in DU13 stay in freshwater for one year\"; \"more vulnerable ... to water management issues (esp. "
                     "Salmon River)\". Status: Endangered (2020).", "sources": [SRC["cosewic"]], "verified": True},
        {"species": "coho", "common": "Coho (Interior Fraser)", "stage": "adults arrive", "months": [10, 11], "scope": "salmon_river",
         "evidence": "Early Nov 2015: \"the coho salmon run is just getting started on the Salmon River\". Spawning months for this "
                     "river were not in a source we could open.", "sources": [SRC["sa_observer"]], "verified": True},
        {"species": "coho", "common": "Coho", "stage": "juveniles rear year-round", "months": months, "scope": "salmon_river",
         "evidence": "BC work windows list coho (CO) in the Salmon River; coho juveniles rear a year in fresh water (general life history).",
         "sources": [SRC["work_windows"]], "verified": True},
        {"species": "sockeye", "common": "Sockeye (Shuswap)", "stage": "present", "months": [], "scope": "not_published",
         "evidence": "BC work windows list sockeye (SK) in the Salmon River, but we found no public source giving Salmon River sockeye "
                     "months. Shuswap-system sockeye generally spawn in early autumn (DFO Fraser sockeye); we leave the strip empty "
                     "rather than guess.", "sources": [SRC["work_windows"]], "verified": False},
    ]
    return {
        "months": months,
        "species": species,
        "irrigation_months": irr_months,
        "irrigation_note": "Months where the engine's current rotation (alfalfa hay) needs at least 5 mm of irrigation on average "
                           "(2015-2025 weather): the overlay for the strip.",
        "critical_window": {"from": "08-01", "to": "09-30",
                            "why": "Lowest flows of the year, warmest water, and adult Chinook entering and spawning: the same "
                                   "weeks the hay field's irrigation need is still high. The orders (16 Aug 2023; 19 Aug 2026) fall here."},
        "note": "Months are from Salmon River sources where we found them; anything Shuswap- or Fraser-general is labelled. Check "
                "local timing with the Secwépemc Fisheries Commission or DFO before acting on it.",
    }


# ------------------------------------------------------------------ 4. early warning
def spearman(a, b):
    m = a.notna() & b.notna()
    if m.sum() < 6:
        return None, int(m.sum())
    return float(a[m].rank().corr(b[m].rank())), int(m.sum())


def build_early_warning(aug_mean: pd.Series):
    rows = pd.DataFrame(index=pd.Index(range(1992, 2027), name="year"))
    rows["aug_mean_m3s"] = aug_mean
    used, missing = [], []
    snow = None
    if (CACHE / "modis_snow.parquet").exists():
        snow = pd.read_parquet(CACHE / "modis_snow.parquet")
        snow["start"] = pd.to_datetime(snow.start)
        snow["doy"] = snow.start.dt.day_of_year
        late = snow[(snow.doy >= 105) & (snow.doy <= 129)]   # composites starting ~15 Apr .. ~9 May
        rows["snow_late_apr_frac"] = late.groupby("year").snow_frac.mean()

        def meltout(g):
            g = g.sort_values("start")
            below = g[(g.doy >= 60) & (g.snow_frac < 0.5)]
            return below.doy.iloc[0] if len(below) else np.nan
        rows["snow_meltout_doy"] = snow.groupby("year").apply(meltout, include_groups=False)
        used.append("MODIS MOD10A2 snow (2001-2026)")
    else:
        missing.append("MODIS snow (run backend/bc/fetch_snow.py)")
    e = pd.read_parquet(CACHE / "eccc.parquet")
    e["date"] = pd.to_datetime(e.date)

    def winter(cid):
        x = e[e.station == cid].set_index("date").prcp_mm.dropna()
        w = x[(x.index.month >= 11) | (x.index.month <= 3)]
        wy_ = np.array([d.year + 1 if d.month >= 11 else d.year for d in w.index])
        cnt = w.groupby(wy_).count()
        return (w.groupby(wy_).sum() * 151 / cnt)[cnt >= 140]
    sc, sa = winter("1167337"), winter("116FRMN")
    both = sc.index.intersection(sa.index)
    ratio = float(sc.loc[both].sum() / sa.loc[both].sum()) if len(both) else 1.0
    wp = sc.combine_first(sa * ratio)
    rows["eccc_nov_mar_precip_mm"] = wp
    winter_note = (f"Silver Creek (1167337, in the Salmon River valley) Nov-Mar total where complete (water years {int(sc.index.min())}-"
                   f"{int(sc.index.max())}); after it closed in 2021, Salmon Arm CS (116FRMN) x {ratio:.2f}, the Silver Creek / Salmon Arm "
                   f"ratio over the {len(both)} winters both were complete. Totals scaled for missing days (>= 140 of 151). A valley-floor "
                   "rough snowpack proxy.")
    used.append("ECCC Silver Creek / Salmon Arm CS winter precipitation")
    if (CACHE / "imerg.parquet").exists():
        im = pd.read_parquet(CACHE / "imerg.parquet")
        im["date"] = pd.to_datetime(im.date)
        im = im.set_index("date").precipitation
        sp = im[(im.index.month >= 3) & (im.index.month <= 6)]
        c = sp.groupby(sp.index.year).count()
        rows["imerg_mar_jun_precip_mm"] = (sp.groupby(sp.index.year).sum() * 122 / c)[c >= 110]
        used.append("NASA GPM IMERG spring precipitation (2015-2026)")
    if (CACHE / "grace.parquet").exists():
        gr = pd.read_parquet(CACHE / "grace.parquet")
        gr["date"] = pd.to_datetime(gr.date)
        my = gr[gr.date.dt.month == 5]
        rows["grace_may_rootzone_pct"] = my.groupby(my.date.dt.year).rtzsm_inst.mean()
        used.append("NASA GRACE-DA root-zone soil moisture percentile, May (2003-2026)")
    if not (CACHE / "smap_l4.parquet").exists():
        missing.append("SMAP L4 (not cached for this field; data/cache/<id>/smap_l4.parquet absent)")

    ind = [
        ("snow_late_apr_frac", "Watershed snow cover, mid-Apr to early May (MODIS)", "fraction", SRC["modis"],
         "Mean snow fraction of the MOD10A2 8-day composites starting 15 Apr-9 May over the Salmon River watershed (FWA group SALR). "
         "8-day maximum extent, so it leans high."),
        ("snow_meltout_doy", "Day the watershed drops below half snow-covered (MODIS)", "day of year", SRC["modis"],
         "Start day of the first MOD10A2 composite after 1 Mar with < 50% of classified watershed pixels snow-covered."),
        ("eccc_nov_mar_precip_mm", "Winter precipitation in the valley (Nov-Mar, ECCC stations)", "mm", SRC["eccc"], winter_note),
        ("imerg_mar_jun_precip_mm", "Spring rain and snow, Mar-Jun (IMERG)", "mm", SRC["imerg"],
         "GPM IMERG daily at the field's 0.1 deg cell, 1 Mar-30 Jun."),
        ("grace_may_rootzone_pct", "Root-zone soil moisture in May (GRACE-DA)", "percentile", SRC["grace"],
         "Mean of the weekly GRACE-DA root-zone soil moisture percentiles in May, 0.25 deg cell at the field."),
    ]
    rows = rows.loc[[y for y in rows.index if rows.loc[y].drop("aug_mean_m3s").notna().any() or not np.isnan(rows.loc[y, "aug_mean_m3s"])]]
    corr, table_cols = [], []
    for col, label, unit, src, note in ind:
        if col not in rows:
            continue
        hist = rows.loc[rows.index <= 2025]
        rho, n = spearman(hist[col], hist.aug_mean_m3s)
        yrs = [int(y) for y in hist.index[hist[col].notna() & hist.aug_mean_m3s.notna()]]
        low_ind = hist[col].dropna()
        low_flow = hist.aug_mean_m3s.dropna()
        both = low_ind.index.intersection(low_flow.index)
        li = low_ind.loc[both]
        lf = low_flow.loc[both]
        # 'low' end of each indicator is the dry end: for melt-out day the dry end is an EARLY melt (low day number too)
        low_years = sorted(int(y) for y in li[li <= li.quantile(1 / 3)].index)
        lowflow_years = set(int(y) for y in lf[lf <= lf.quantile(1 / 3)].index)
        hits = [y for y in low_years if y in lowflow_years]
        v26 = rows[col].get(2026) if 2026 in rows.index else None
        corr.append({
            "indicator": col, "label": label, "unit": unit,
            "spearman_r": sn(rho, "", "computed", src, f"Rank correlation with the August mean flow at 08LE021 over {n} years "
                             f"({yrs[0] if yrs else ''}-{yrs[-1] if yrs else ''}). Positive = drier spring, lower August flow.", nd=2),
            "n_years": n, "years": yrs,
            "driest_third_years": low_years,
            "driest_third_with_low_august": hits,
            "hit_rate": sn(len(hits) / len(low_years) if low_years else None, "fraction", "computed", src,
                           "Share of the driest-third years of this indicator whose August flow was also in the lowest third "
                           "(1/3 by chance)." , nd=2),
            "value_2026": sn(v26, unit, "measured" if col != "snow_meltout_doy" else "computed", src, note),
            "pct_rank_2026": sn(pct_rank(v26, hist[col].values) if v26 is not None and not pd.isna(v26) else None, "percentile",
                                "computed", src, "Where 2026 sits among the earlier years (0 = driest)."),
        })
        table_cols.append(col)
    table = [{"year": int(y), "aug_mean_m3s": r(v.aug_mean_m3s, 3), **{c: r(v[c], 3) for c in table_cols}} for y, v in rows.iterrows()]
    return {
        "label": "Rule of thumb, not a forecast model",
        "question": "Does a thin spring (less snow, less rain, drier soil) line up with a low August river?",
        "indicators": corr,
        "table": table,
        "table_units": {"aug_mean_m3s": "m3/s", **{c: u for c, _, u, _, _ in ind if c in table_cols}},
        "used": used, "missing": missing,
        "note": "Correlations over 11-34 years, with flows also shaped by summer rain, heat and water use: a hint for when to start "
                "watching the gauge, not a prediction. IMERG covers only 2015 on, so its correlation rests on ~11 years.",
    }


# ------------------------------------------------------------------ 5. water left for salmon
EFF = (0.75, 0.6, 0.85)    # application efficiency (sprinkler), assumed


def monthly_need():
    from rotation_engine import engine as E  # noqa: PLC0415
    from rotation_engine.model import EFFECTIVE_RAIN  # noqa: PLC0415
    from rotation_engine.timeline import build_timeline  # noqa: PLC0415
    crops = E.load_crops()
    out = {}
    for label, yrs in (("mean_2015_2025", E.DEFAULT_YEARS), ("2023", (2023,))):
        wys = E.weather_years(FID, yrs, 0.0, 0.0)
        for s in E.load_strategies(FID):
            tl = build_timeline(s, crops)
            N, m = tl.n_years, np.zeros(12)
            for wy in wys:
                etc = tl.kc["value"] * np.tile(wy.eto, N)
                p = np.tile(wy.p["power"], N)
                for sp in tl.spans:   # same balance as rotation_engine.model.water_metrics
                    if not sp.entry.get("irrigated"):
                        continue
                    key = tl.cyear[sp.idx] * 12 + (tl.month[sp.idx] - 1)
                    uk, inv = np.unique(key, return_inverse=True)
                    need = np.maximum(0.0, np.bincount(inv, weights=etc[sp.idx]) - EFFECTIVE_RAIN * np.bincount(inv, weights=p[sp.idx]))
                    np.add.at(m, uk % 12, need)
            out.setdefault(s["id"], {"strategy": s})[label] = m / N / len(wys)
    return out


def build_rotations(mad, p10_aug, flow_order_years):
    sf = REPO / "backend/engine/out" / FID / "strategies.json"
    st = jload(sf)
    st = st.get("items", st) if isinstance(st, dict) else st
    stored = {s["id"]: s for s in st}
    need = monthly_need()
    secs = 61 * 86400
    low_aug = {oy["year"]: oy["aug_mean"]["value"] for oy in flow_order_years}
    items = []
    for sid, v in need.items():
        m, m23 = v["mean_2015_2025"], v["2023"]
        s = stored.get(sid, v["strategy"])
        engine_total = (s.get("water") or {}).get("irrigation_need_mm", {}).get("value")
        net = float(m[7] + m[8])
        net23 = float(m23[7] + m23[8])
        gross = net / EFF[0]
        m3 = gross / 1000 * FIELD_HA * 1e4
        lps = m3 / secs * 1000
        ref_note = f"our reference low August flow, the {REF[0]}-{REF[1]} 10th percentile of August daily flow at 08LE021 ({p10_aug:.2f} m³/s)"
        items.append({
            "strategy_id": sid, "short_name": s.get("short_name"), "name": s.get("name"),
            "irrigated_in_window": net > 0.5,
            "monthly_need_mm": [r(x, 1) for x in m],
            "net_need_aug_mm": sn(m[7], "mm", "computed", SRC["engine"], "Engine water balance, August, mean of 2015-2025 weather."),
            "net_need_sep_mm": sn(m[8], "mm", "computed", SRC["engine"], "September, mean of 2015-2025 weather."),
            "net_need_aug_sep_mm": sn(net, "mm", "computed", SRC["engine"],
                                      "Crop irrigation need Aug+Sep: sum of monthly max(0, ETc - 0.8 x rain) over the irrigated crops, per "
                                      "cycle year, 2015-2025 weather (the same balance as the engine's irrigation_need_mm"
                                      + (f", whose yearly total is {engine_total} mm" if engine_total is not None else "") + ")."),
            "net_need_aug_sep_mm_2023_weather": sn(net23, "mm", "computed", SRC["engine"], "Same, in 2023's weather (a drought year)."),
            "draw_aug_sep_mm": sn(gross, "mm", "computed", SRC["engine"],
                                  f"Water taken from the river or aquifer = net need / {EFF[0]} application efficiency (sprinkler, assumed); "
                                  f"range for efficiency {EFF[2]}-{EFF[1]}.", low=net / EFF[2], high=net / EFF[1], nd=1),
            "draw_aug_sep_m3": sn(m3, "m3", "computed", SRC["engine"], f"draw_aug_sep_mm x {FIELD_HA} ha field.",
                                  low=net / EFF[2] / 1000 * FIELD_HA * 1e4, high=net / EFF[1] / 1000 * FIELD_HA * 1e4, nd=0),
            "draw_rate_l_s": sn(lps, "L/s", "computed", SRC["engine"], "The Aug-Sep draw spread evenly over 61 days (pumps really run in "
                                "sets, so the instantaneous rate is higher).", nd=2),
            "share_of_low_aug_flow_pct": sn(100 * lps / 1000 / p10_aug, "%", "computed", SRC["hydat"],
                                            f"draw_rate_l_s as a share of {ref_note}.", nd=2),
            "share_of_aug_2023_flow_pct": sn(100 * lps / 1000 / low_aug[2023], "%", "computed", SRC["hydat"],
                                             f"Share of the August 2023 mean flow ({low_aug[2023]:.2f} m³/s).", nd=2),
            "share_of_aug_2026_flow_pct": sn(100 * lps / 1000 / low_aug[2026], "%", "computed", SRC["rt"],
                                             f"Share of the August 2026 mean flow ({low_aug[2026]:.2f} m³/s, provisional).", nd=2),
        })
    base = next(i for i in items if i["strategy_id"].startswith("bc0"))
    scale = []
    for lic, yr, src in ((398, 2023, SRC["bc_2023"]), (458, 2026, SRC["bc_2026"])):
        for ha in (5.0, 10.0, FIELD_HA):
            lps = base["draw_rate_l_s"]["value"] / FIELD_HA * ha * lic
            scale.append({
                "licences": sn(lic, "licences", "lookup", src, f"Licences under the {yr} order" + (" (lower Salmon River and Bessette Creek together)" if yr == 2023 else " (Salmon River watershed)")),
                "assumed_ha_per_licence": sn(ha, "ha", "assumed", SRC["assumed"] if ha != FIELD_HA else SRC["registry"],
                                             "Illustration only: we do not know the irrigated area per licence; some holders have several "
                                             "licences and not all irrigate hay." + (" 21.5 ha = this field." if ha == FIELD_HA else "")),
                "draw_rate_l_s": sn(lps, "L/s", "computed", SRC["engine"], "Today's rotation (alfalfa) draw rate x licences x assumed area.", nd=0),
                "share_of_low_aug_flow_pct": sn(100 * lps / 1000 / p10_aug, "%", "computed", SRC["hydat"],
                                                f"Against our reference low August flow ({p10_aug:.2f} m³/s). Over 100% means the demand is larger "
                                                "than the river carries in a low August.", nd=0),
            })
    return {
        "window": {"from": "08-01", "to": "09-30", "days": 61},
        "field_area": sn(FIELD_HA, "ha", "measured", SRC["registry"], "Polygon area of the field outline."),
        "reference_low_flow": sn(p10_aug, "m3/s", "computed", SRC["hydat"], f"10th percentile of August daily flow, {REF[0]}-{REF[1]}, 08LE021."),
        "efficiency": sn(EFF[0], "fraction", "assumed", SRC["assumed"], "Sprinkler application efficiency (share of pumped water the crop "
                         "can use).", low=EFF[1], high=EFF[2]),
        "items": items,
        "scale_up": {"label": "Illustration: if every forage field in the order area did this", "rows": scale,
                     "note": "Not an estimate of real water use. Licences are counts from BC's releases; the area per licence is assumed. "
                             "Groundwater licences are included because BC counts them under the orders (wells near the river draw on it)."},
        "note": "One 21.5 ha field is a small share of the river; the orders exist because hundreds of licences add up, in the weeks "
                "when the river is lowest. A rotation with no Aug-Sep irrigation (dryland sainfoin-grass) leaves that water in the river.",
    }


# ------------------------------------------------------------------ 6. summary + respect
def summary(flow, temp, ew, rot):
    oy = {o["year"]: o for o in flow["order_years"]}
    t26 = next((s for st in temp["stations"] if st["station"] == GAUGE for s in st["summers"] if s["year"] == 2026), None)
    base = next(i for i in rot["items"] if i["strategy_id"].startswith("bc0"))
    sf = next((i for i in rot["items"] if i["strategy_id"].startswith("bc3")), None)
    lines = [
        f"In August 2026 the Salmon River near Salmon Arm averaged {oy[2026]['aug_mean']['value']:.2f} m³/s, "
        f"{oy[2026]['aug_mean_pct_of_normal']['value']:.0f}% of a normal August, and spent {oy[2026]['days_below_order_trigger_aug_sep']['value']:.0f} "
        "days of Aug-Sep below the 0.625 m³/s level in the 2026 protection order.",
        f"August 2023 averaged {oy[2023]['aug_mean']['value']:.2f} m³/s; the 2023 order's level was 1.27 m³/s.",
    ]
    if t26:
        lines.append(f"Water temperature at the gauge reached {t26['peak']['value']:.1f} °C in summer 2026, with "
                     f"{t26['days_max_ge_18']['value']:.0f} days that reached 18 °C (salmon swim less well) and "
                     f"{t26['days_max_ge_20']['value']:.0f} that reached 20 °C (high pre-spawn mortality risk) between June and September.")
    lines.append("Adult Chinook enter in August and spawn in September, the same weeks hay fields still want water.")
    lines.append(f"This field's current hay rotation would draw about {base['draw_aug_sep_m3']['value']:,.0f} m³ in Aug-Sep "
                 f"({base['draw_rate_l_s']['value']:.1f} L/s, about {base['share_of_low_aug_flow_pct']['value']:.1f}% of a low August "
                 "flow). Small alone; hundreds of licences together can match the whole river."
                 + (" The dryland sainfoin-grass rotation draws none." if sf and not sf["irrigated_in_window"] else ""))
    best = max((i for i in ew["indicators"] if i["spearman_r"]["value"] is not None and i["n_years"] >= 20),
               key=lambda i: i["spearman_r"]["value"], default=None)
    if best:
        lines.append(f"Early hint (rule of thumb, not a forecast): of the indicators with 20+ years, {best['label'].split(' (')[0].lower()} "
                     f"lines up best with August flow (rank correlation {best['spearman_r']['value']:.2f} over {best['n_years']} years; "
                     f"{len(best['driest_third_with_low_august'])} of its {len(best['driest_third_years'])} driest-third years had a low August).")
    return lines


def respect(fn):
    return {
        "public_data_only": True,
        "reserve_land_analysed": False,
        "statements": [
            "Public data only: Water Survey of Canada gauges, BC orders and guidelines, DFO and NASA satellite records.",
            "No reserve land was analysed.",
            "Built to be co-developed; we'd welcome the Nation's guidance on what matters.",
            "Nothing here speaks for any Nation, and no partnership exists or is implied.",
            "Splatsin's Territorial Water Manager and the Secwépemc Fisheries Commission already watch low flows on the Swawll "
            "Setatkwa (Salmon River) with their own monitoring; their knowledge comes first.",
        ],
        "links": [{"title": "Splatsin: Your Government, Land (Lands Department; Territorial Water Manager)",
                   "url": (fn or {}).get("lower_river_nation", {}).get("url", SRC["splatsin"]["url"]), "verified": True},
                  {"title": "Shuswap Nation Tribal Council: Secwépemc Fisheries Commission", "url": "https://shuswapnation.org/fisheries/", "verified": True},
                  {"title": "Pacific Salmon Foundation: Smarter drought monitoring for salmon", "url": SRC["psf"]["url"], "verified": True}],
        "first_nations_route": f"/api/locations/{FID}/first_nations",
    }


# ------------------------------------------------------------------ main
def main():
    d, meta = load_wsc()
    flow, mad, p10_aug, aug_mean = build_flow(d, meta)
    temp = build_temperature(d, meta)
    rot = build_rotations(mad, p10_aug, flow["order_years"])
    base = next(i for i in rot["items"] if i["strategy_id"].startswith("bc0"))
    irr_months = [k + 1 for k, v in enumerate(base["monthly_need_mm"]) if (v or 0) >= 5]
    ew = build_early_warning(aug_mean)
    fn_p = OUT / "first_nations.json"
    fn = jload(fn_p) if fn_p.exists() else None
    reg = jload(REPO / "backend/fields/registry.json")["fields_other_regions"][0]
    c = reg["centroid"]
    stations = []
    for stn in (GAUGE, UPPER):
        i = meta["stations"][stn]
        stations.append({
            "id": stn, "name": i["name"].title(), "lat": i["lat"], "lon": i["lon"], "role": i["role"], "operator": i["operator"],
            "drainage_area": sn(i["drainage_km2"], "km2", "lookup", SRC["hydat"] if stn == GAUGE else SRC["hydat_up"]),
            "distance_from_field": sn(km(c["lat"], c["lon"], i["lat"], i["lon"]), "km", "computed", SRC["registry"],
                                      "Straight line from the field centroid.", nd=1),
            "url": f"https://wateroffice.ec.gc.ca/report/real_time_e.html?stn={stn}",
        })
    g = meta["stations"][GAUGE]
    gu = meta["stations"][UPPER]
    series_meta = {
        "flow_daily": {"station": GAUGE, "unit": "m3/s", "first": g["discharge_first"], "last": g["discharge_last"],
                       "approved_to": g["hydat_last"], "provisional_from": g["provisional_first"], "served_from": flow["daily"][0]["date"],
                       "note": "Full record from 1911 with gaps (continuous from 1974); /salmon serves daily rows from 2015, the full record as August means."},
        "flow_realtime_latest": {"station": GAUGE, "unit": "m3/s", "datetime_utc": (g.get("latest_realtime") or {}).get("datetime_utc"),
                                 "datetime_local": (g.get("latest_realtime") or {}).get("datetime_local")},
        "flow_percentiles": {"unit": "m3/s", "reference_period": list(REF), "window": "+/-7 days"},
        "water_temp_daily": {s["station"]: {"unit": "degC", "first": s["first"], "last": s["last"]} for s in temp["stations"]},
        "upper_flow_daily": {"station": UPPER, "unit": "m3/s", "first": gu["discharge_first"], "last": gu["discharge_last"]},
        "snow": {"unit": "fraction", "first_year": 2001, "last_year": 2026},
        "irrigation": {"unit": "mm (depth on the field) and m3 (volume for 21.5 ha)", "window": "Aug-Sep"},
        "fetched_at": meta["fetched_at"],
    }
    payload = {
        "location_id": FID,
        "title": "Salmon and the field",
        "river": "Salmon River (Swawll Setatkwa), Shuswap, BC",
        "generated_at": meta["fetched_at"][:10],
        "series_meta": series_meta,
        "stations": stations,
        "flow": flow,
        "temperature": temp,
        "run_timing": run_timing(irr_months),
        "early_warning": ew,
        "water_for_salmon": rot,
        "summary": summary(flow, temp, ew, rot),
        "respect": respect(fn),
        "sources": list(SRC.values()),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "salmon.json").write_text(json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":")) + "\n")
    print(f"wrote {OUT / 'salmon.json'} ({(OUT / 'salmon.json').stat().st_size / 1e3:.0f} kB)")
    print("\n".join(payload["summary"]))
    for i in ew["indicators"]:
        print(i["indicator"], i["spearman_r"]["value"], i["n_years"], i["hit_rate"]["value"])


if __name__ == "__main__":
    main()
