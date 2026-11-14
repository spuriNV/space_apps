"""Source registry and SourcedNumber helpers (spec B3).

Every number the engine emits is a SourcedNumber:
  {value, unit, low, high, method, source{id,title,url,accessed,verified}, note}

Rules used here (CONTRACT.md, "Data honesty"):
- V items from the spec -> method "lookup", verified True, source = the cited page.
- U items -> method "assumed", verified False, source = the spec section that
  marks them U (`to_cite` says where a real citation should come from).
- Blocked inputs -> value None with a note naming what is missing.
"""
from __future__ import annotations

import copy
import math

ACCESSED = "2026-11-14"
SPEC_URL = "planner-spec.md#b4-scoring-model"  # repo-relative; the spec is the source of every U value

SOURCES: dict[str, dict] = {
    "fao56_table12": {
        "title": "FAO-56 Chapter 6, Table 12 (single crop coefficients Kc ini/mid/end)",
        "url": "https://www.fao.org/4/x0490e/x0490e0b.htm", "verified": True},
    "fao56_table11": {
        "title": "FAO-56 Chapter 6, Table 11 (lengths of crop development stages)",
        "url": "https://www.fao.org/4/x0490e/x0490e0b.htm", "verified": True},
    "fao56_eq52": {
        "title": "FAO-56 Chapter 3, Hargreaves ETo (eq. 52) and extraterrestrial radiation Ra (eq. 21)",
        "url": "https://www.fao.org/4/x0490e/x0490e07.htm", "verified": True},
    "fao56_kc_curve": {
        "title": "FAO-56 Chapter 6, constructing the Kc curve (linear interpolation between stages)",
        "url": "https://www.fao.org/4/x0490e/x0490e0b.htm", "verified": True},
    "fao56_eq6": {
        "title": "FAO-56 Chapter 2 eq. 6 (Penman-Monteith grass reference ETo) and Chapter 3 eqs. 7-19, 37-39",
        "url": "https://www.fao.org/4/x0490e/x0490e06.htm", "verified": True},
    "ncei_ghcnd": {
        "title": "NOAA NCEI GHCN-Daily station Tmax/Tmin/PRCP (regional chunk cache, 3 nearest long-record stations)",
        "url": "https://www.ncei.noaa.gov/access/services/data/v1", "verified": True},
    "nasa_power_daily": {
        "title": "NASA POWER daily point API (AG community)",
        "url": "https://power.larc.nasa.gov/api/temporal/daily/point", "verified": True},
    "uc_rice_blog": {
        "title": "UC Rice Blog (planting dates, 145-150 day season)",
        "url": "https://www.ucanr.edu/blog/uc-rice-blog", "verified": True},
    "uc_alfalfa": {
        "title": "UC Alfalfa & Forage, irrigated alfalfa (SJV planting window, cutting schedule)",
        "url": "https://alfalfa.ucdavis.edu/IrrigatedAlfalfa", "verified": True},
    "ssurgo_sda": {
        "title": "USDA NRCS SSURGO via Soil Data Access (regional chunk cache)",
        "url": "https://sdmdataaccess.sc.egov.usda.gov/", "verified": True},
    "unit_definition": {
        "title": "NIST SP 811 Appendix B.8: foot = 3.048 E-01 m (exact); 1 acre-foot per acre = 1 ft of water depth = 304.8 mm",
        "url": "https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8",
        "verified": True},
    "field_shift_engine": {
        "title": "Field Shift rotation engine, formula from planner-spec B4 (rule of thumb, not a model)",
        "url": SPEC_URL, "verified": False},
    "assumed": {
        "title": "Team assumption marked U in planner-spec; not from a cited source",
        "url": SPEC_URL, "verified": False},
    "covercrop_selector": {
        "title": "Western Cover Crop Council selector (ratings to be transcribed by hand; not yet done)",
        "url": "https://covercrop-selector.org", "verified": False},
    # Blocked sources (keys or downloads we do not have yet)
    "openet": {"title": "OpenET Ensemble v2.1 monthly actual ET over the field polygon (backend/ground cache; "
                         "validation only, never a score input)",
               "url": "https://openet-api.org/raster/timeseries/polygon", "verified": True},
    "rma_col": {"title": "USDA RMA cause of loss (yearly files not yet downloaded/processed)",
                "url": "https://www.rma.usda.gov/tools-reports/summary-business/cause-loss", "verified": False},
    "nass_quickstats": {"title": "USDA NASS Quick Stats prices (API key required)",
                        "url": "https://quickstats.nass.usda.gov/", "verified": False},
    "ams_mymarketnews": {"title": "USDA AMS My Market News California hay reports (API key required)",
                         "url": "https://marsapi.ams.usda.gov/services/v1.2/reports", "verified": False},
    "eqip_340": {"title": "USDA NRCS EQIP practice 340 Cover Crop, California payment schedule (rate not transcribed)",
                 "url": "https://www.nrcs.usda.gov/programs-initiatives/eqip-environmental-quality-incentives-program",
                 "verified": False},
    "cimis": {"title": "CIMIS station ETo (API key required)", "url": "https://et.water.ca.gov/", "verified": False},
    "gpm_imerg": {"title": "GPM IMERG daily precipitation (Earthdata login required)",
                  "url": "https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary", "verified": False},
    "cal_adapt": {"title": "Cal-Adapt 2050s scenario values (not transcribed)", "url": "https://cal-adapt.org",
                  "verified": False},
}


def src(key: str, **extra) -> dict:
    s = SOURCES[key]
    out = {"id": key, "title": s["title"], "url": s["url"], "accessed": ACCESSED, "verified": s["verified"]}
    out.update(extra)
    return out


def _clean(x):
    if x is None:
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return x


def sn(value, unit: str, *, low=None, high=None, method: str, source: dict, note: str = "", rnd: int | None = None,
       **extra) -> dict:
    """Build a SourcedNumber. low/high default to value."""
    value, low, high = _clean(value), _clean(low), _clean(high)
    if value is not None:
        low = value if low is None else low
        high = value if high is None else high
        if rnd is not None:
            value, low, high = round(value, rnd), round(low, rnd), round(high, rnd)
    d = {"value": value, "unit": unit, "low": low, "high": high, "method": method,
         "source": copy.deepcopy(source), "note": note}
    d.update(extra)
    return d


def lookup(value, unit, key, *, low=None, high=None, note="") -> dict:
    """A V value copied from the spec's quote of a cited source."""
    return sn(value, unit, low=low, high=high, method="lookup", source=src(key), note=note)


def assumed(value, unit, *, low, high, note, to_cite: str | None = None) -> dict:
    """A U value: method assumed, verified False, always with a range."""
    d = sn(value, unit, low=low, high=high, method="assumed", source=src("assumed"), note=note)
    if to_cite:
        d["to_cite"] = to_cite
    return d


def blocked(unit: str, key: str, note: str, method: str = "lookup") -> dict:
    """A value we cannot fill (missing key/data). Never invented."""
    return sn(None, unit, method=method, source=src(key), note="BLOCKED: " + note, blocked=True)
