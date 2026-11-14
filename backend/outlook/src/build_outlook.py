"""Assemble out/<preset>/outlook.json from out/{cpc,water_now,context,history,irrigation}.json. Offline."""
from common import *

def sent_count(s): return len([x for x in s.replace("e.g.", "eg").split(". ") if x.strip()])

def af(v): return f"{v:,.0f}"

def summary(pid, cpc, wn, hist, irr, ctx):
    c = {s["season"]: s for s in cpc["seasons"]}
    prec = lambda s: c[s]["precipitation"]; tmp = lambda s: c[s]["temperature"]
    def tilt(x, what):
        if x["category"] == "equal chances": return f"no tilt for {what}"
        return f"a {x['probability']['value']:.0f}% chance of {x['category']} {what}"
    parts = []
    if pid == "car_colusa_rice":
        parts.append(f"This is an outlook, not a forecast: NOAA's Climate Prediction Center gives {tilt(prec('DJF'), 'rain')} for Dec-Feb and {tilt(prec('FMA'), 'rain')} for Feb-Apr, and {tilt(tmp('DJF'), 'temperature')} for Dec-Feb (about 33% is what any category gets in an average year).")
    else:
        parts.append(f"This is an outlook, not a forecast: NOAA's Climate Prediction Center gives {tilt(prec('DJF'), 'rain')} for Dec-Feb and {tilt(prec('JFM'), 'rain')} for Jan-Mar, with {tilt(tmp('DJF'), 'temperature')} for Dec-Feb (about 33% is what any category gets in an average year).")
    res = wn["reservoirs"]
    if pid == "car_colusa_rice":
        s, o = res["SHA"], res["ORO"]
        parts.append(f"Shasta holds {af(s['storage_af']['value'])} acre-feet ({s['pct_of_cdec_average']['value']:.0f}% of CDEC's average for 13 Nov) and Oroville {af(o['storage_af']['value'])} acre-feet ({o['pct_of_cdec_average']['value']:.0f}% of average).")
    else:
        s = res["PNF"]
        parts.append(f"Pine Flat holds {af(s['storage_af']['value'])} acre-feet, {s['pct_of_cdec_average']['value']:.0f}% of CDEC's average for 13 Nov and {s['pct_of_capacity']['value']:.0f}% full.")
    dm = wn["drought_monitor"]; d0 = dm["area_in_category_percent"]["D0"]["value"]
    sdo = cpc["drought_outlook"]["seasonal"]["category"].replace("_", " ").lower()
    parts.append(f"The Drought Monitor week of {dm['map_date']} shows {dm['worst_category'].split(' ',1)[1] if d0 else 'no drought or dryness'} ({d0:.0f}% of the county at the D0 level or worse), and NOAA's drought outlook through 31 Jan shows {sdo}.")
    h = hist.get("heavy_rain_in_window"); strat = irr["strategies"]; b = next(x for x in strat if x["is_baseline"])["irrigation_need_af_ac"]
    if h:
        parts.append(f"The field is usually bare from about {hist['bare_window']['median_start']} to {hist['bare_window']['median_end']}; in {h['chance_any_day_ge_25mm_climatology']['value']:.0f}% of past winters a 1-inch rain day fell in that window, and about {h['chance_given_cpc_outlook']['value']:.0f}% when weighted by the rain outlook (range {h['chance_given_cpc_outlook']['low']:.0f}-{h['chance_given_cpc_outlook']['high']:.0f}%).")
    else:
        parts.append(f"Alfalfa kept this field covered through most winters, so there is no typical bare window to report (only {hist['winters_with_bare_window']} of {len(hist['winters_with_current_crop'])} winters had 14 or more bare days).")
    parts.append(f"Under the outlook scenario, the current rotation needs about {b['value']:.1f} acre-feet per acre in 2027 (range {b['low']:.1f}-{b['high']:.1f}), little changed from a normal year.")
    return " ".join(parts)

def main():
    cpc, wn, ctx, hist, irr = (read_json(OUT / f) for f in ("cpc.json", "water_now.json", "context.json", "history.json", "irrigation.json"))
    for pid in PRESETS:
        p = {"preset_id": pid, "label": LABEL + " (CPC sections); observations elsewhere", "generated_at": now(), "county": COUNTY[pid][1] + " County", "county_fips": COUNTY[pid][0],
             "today": "2026-11-14", "coming_season": "winter 2026-27 and the 2027 growing season",
             "cpc_seasonal_outlook": {"point": cpc["presets"][pid]["point"], "machine_readable_sources": cpc["files"], "note": cpc["source_note"],
                 "issued": cpc["presets"][pid]["seasons"][0]["temperature"]["issued"],
                 "next_issue": "CPC issues the next 90-day outlook on the third Thursday (19 Nov 2026); the Oct issue is the latest published today.", "seasons": cpc["presets"][pid]["seasons"]},
             "drought": {"us_drought_monitor": wn["presets"][pid]["drought_monitor"], "cpc_drought_outlook": cpc["presets"][pid]["drought_outlook"]},
             "reservoirs_now": wn["presets"][pid]["reservoirs"],
             "snowpack_runoff": {"snow_now_statewide": ctx["snow_now"], "bulletin_120": ctx["bulletin_120"]},
             "allocations_context": {"cvp": ctx["allocations"]["cvp"], "swp": ctx["allocations"]["swp"], "storage_vs_final_allocation": ctx["allocations"]["storage_vs_final_allocation"]},
             "field_expectations_from_history": hist["presets"][pid],
             "irrigation_2027": irr["presets"][pid]}
        p["field_expectations_from_history"] = {k: v for k, v in hist["presets"][pid].items() if k != "scenario"} | {"scenario_inputs": hist["presets"][pid]["scenario"]}
        p["plain_language_summary"] = summary(pid, cpc["presets"][pid], wn["presets"][pid], hist["presets"][pid], irr["presets"][pid], ctx)
        p["blocked_or_not_yet_published"] = [
            {"item": "Bulletin 120 WY2027 forecast", "status": "not yet published", "url_tried": B120},
            {"item": "SWP initial 2027 allocation", "status": "not yet announced (due by 1 Dec)", "url_tried": "https://water.ca.gov/News/News-Releases/2025/Dec-25/SWP-Allocation"},
            {"item": "CVP initial 2027 allocation", "status": "not yet announced", "url_tried": "https://www.usbr.gov/mp/cvo/vungvari/water_allocations_historical.pdf"},
            {"item": "SWP past final allocations and DWR release pages", "status": "blocked: HTTP 403 to automated fetch", "url_tried": "https://water.ca.gov/-/media/DWR-Website/Web-Pages/Programs/State-Water-Project/Management/SWP-Water-Contractors/Files/Historical-SWP-allocations-1996-2024-112923.pdf"},
            {"item": "CPC November 2026 seasonal outlook", "status": "issued 19 Nov 2026; not yet out", "url_tried": "https://ftp.cpc.ncep.noaa.gov/GIS/us_tempprcpfcst/"}]
        write_json(OUT / pid / "outlook.json", p)
        print(pid, "\n", p["plain_language_summary"])

B120 = "https://cdec.water.ca.gov/reportapp/javareports?name=B120UP"
if __name__ == "__main__":
    main()
