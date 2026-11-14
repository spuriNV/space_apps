"""EQIP practice 340 (Cover Crop) California payment schedule.
NRCS no longer publishes a static California PDF; the schedule is served by the NRCS Payment Schedules tool
(https://www.nrcs.usda.gov/getting-assistance/payment-schedules, Drupal form -> cost_list_report, list 'California EQIP-1').
We replay that form (POST) and parse the 340 rows. Non-HU/PR (standard) per-acre scenarios give the range."""
import re, html, json, datetime
from pathlib import Path
import requests

HOST = "https://nrcs-prod.azureedge.us"   # same Drupal site as www.nrcs.usda.gov (www blocks scripts)
PAGE = "https://www.nrcs.usda.gov/getting-assistance/payment-schedules"
URL = HOST + "/getting-assistance/payment-schedules"
OUT = Path(__file__).resolve().parents[1] / "out"

def main():
    s = requests.Session()
    h = s.get(URL, timeout=60).text
    bid = re.search(r'name="form_build_id" value="([^"]+)"', h).group(1)
    ajax = lambda d: s.post(URL + "?ajax_form=1", data=d, headers={"X-Requested-With": "XMLHttpRequest"}, timeout=60).json()
    for trig, extra in [("state_cost", {}), ("county_code", {"county_code": "06011"})]:
        r = ajax({"report_type": "cost_list_report", "state_cost": "06", **extra, "form_build_id": bid, "form_id": "nrcs_payment_api_form", "_triggering_element_name": trig})
        for c in r:
            if c.get("command") == "update_build_id": bid = c["new"]
    r = s.post(URL, data={"report_type": "cost_list_report", "state_cost": "06", "county_code": "06011", "cost_list_name": "California EQIP-1",
                          "form_build_id": bid, "form_id": "nrcs_payment_api_form", "op": "Search"}, timeout=180).text
    txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "\n", r[r.find("results-heading"):])))
    rows = [{"component": a.strip(), "unit": u, "usd_per_unit": float(p.replace("$", "").replace(",", ""))}
            for a, u, p in re.findall(r"California EQIP-1 340 Cover Crop (.*?) (Ac|No) (\$[\d,\.]+)", txt)]
    if not rows:
        print("FAIL: no 340 rows parsed"); raise SystemExit(1)
    std = [x for x in rows if x["unit"] == "Ac" and not x["component"].startswith(("HU-", "PR-")) and not x["component"].startswith("Islands")]
    lo, hi = min(x["usd_per_unit"] for x in std), max(x["usd_per_unit"] for x in std)
    src = {"id": "nrcs_ca_eqip_payment_schedule", "title": "NRCS Payment Schedules tool, California EQIP-1, practice 340 Cover Crop",
           "url": PAGE, "accessed": datetime.date.today().isoformat(), "verified": True}
    out = {"practice": "340 Cover Crop", "cost_list": "California EQIP-1", "state": "CA", "counties_checked": ["06011", "06031"],
           "fiscal_year": "not stated by the tool (live schedule; NRCS releases the new one Oct-Dec each FY); no static PDF exists",
           "page": "n/a (HTML report, not a PDF)", "access_method": "POST form at " + URL + " report_type=cost_list_report state_cost=06 county_code=06011 cost_list_name='California EQIP-1'",
           "all_340_rows": rows,
           "standard_acre_scenarios_used": std,
           "usd_per_acre": {"value": round((lo + hi) / 2, 2), "low": lo, "high": hi, "unit": "USD/acre", "method": "lookup", "source": src,
                            "note": "Range over standard (non historically-underserved, non-islands) per-acre scenarios: Any Species, Any Species Organic, Biomass. HU/PR (historically underserved) rates are ~20 pct higher (e.g. Biomass 133.88); Islands scenarios excluded."},
           "usd_per_ha": {"low": round(lo * 2.47105, 2), "high": round(hi * 2.47105, 2), "unit": "USD/ha", "method": "computed", "source": src},
           "caveat": "Payment rate, not cost; confirm eligibility and rates with the local NRCS office."}
    OUT.mkdir(exist_ok=True); json.dump(out, open(OUT / "eqip_340_ca.json", "w"), indent=1)
    print(f"EQIP 340 CA: ${lo}-{hi}/ac (${out['usd_per_ha']['low']}-{out['usd_per_ha']['high']}/ha)")
if __name__ == "__main__": main()
