"""Response-layer clean-up for user-facing text and source links. Applied once, in main.send(), to real and estimate payloads.

1. Text: strips the team's internal markers from strings shown to users (names, notes, labels, local_review items, brief
   text, source titles): "(U)", "(V)", "U:"/"V:" prefixes inside brackets, "spec B11", "(spec B4.4)", "planner-spec B4" and a
   few whole phrases that only make sense inside the repo. The data status is NOT taken from these markers: `method`,
   `verified`, ids, units, dates and URLs are never touched.
2. Links: a `url` / `source_url` that is a repo path (backend/..., data/cache/..., docs/..., planner-spec.md), an internal
   urn:fieldshift:* id or a GitHub blob path is replaced by the dataset's public page when PUBLIC_URLS knows one; otherwise
   it is kept and its object gets `internal: true` (show the title, do not link). A bare domain gets https://.

Source files are left as they are; only responses change.
"""
from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------- text
# Keys whose string values are machine fields: never rewritten.
SKIP_KEYS = {"id", "url", "source_url", "method", "verified", "meta_path", "unit", "units", "type", "layer", "crop_id", "role",
             "query_id", "key", "status", "date", "plant", "harvest", "terminate", "cell_id", "region", "region_adapter", "family",
             "template", "_source", "geometry", "severity", "detector", "model", "kind", "category", "class", "cover_class",
             "cover_source", "power_run", "imerg_run", "location_id", "field_id", "mukey", "dwr_unique_id", "grid"}

# Whole phrases first (exact substrings), then the generic marker patterns.
PHRASES = [
    ("Field Shift rotation engine, formula from planner-spec B4 (rule of thumb, not a model)", "CropLytics rotation engine (rule of thumb, not a model)"),
    ("Team assumption marked U in planner-spec; not from a cited source", "Team assumption; not from a cited source"),
    ("spec marks the event V (news) but gives no URL", "Reported in the news; no source link yet"),
    ("spec marks V but gives no URL", "Reported in the news; no source link yet"),
    (" (spec marks V; URL not in spec)", ""),
    ("spec statement (U)", "Assumed for this example field"),
    ("U rule of thumb (spec B5.1), not tuned", "Rule of thumb, not tuned"),
    ("Spec B1 CAR2 trigger (U)", "Assumed trigger for the dry-year plan"),
    ("(stated by spec; not cited)", "(not cited)"),
    ("are spec statements marked U", "are assumed example values"),
    ("marked U", "assumed"),
    (" (see README)", ""),
]
_TOKEN = r"(?:U|V)"
_SPEC = r"(?:planner-)?[Ss]pec B\d+(?:\.\d+)*"
PATTERNS = [
    (re.compile(r"\s*\((?:see |fix of )?" + _SPEC + r"(?:[,;][^)]*)?\)"), ""),             # "(spec B11)", "(spec B4.4, see ...)"
    (re.compile(r"[;,]\s*" + _SPEC + r"(?=\s*[.;,)]|\s*\(|$)"), ""),                       # "...DEM; spec B7.3 (U)."
    (re.compile(r"\b(?:[Ff]ix of )" + _SPEC), "Adjusted formula"),                         # "Fix of spec B4.7 (see README): ..."
    (re.compile(_SPEC + r"(?: quote| table rule)?\s*[:;,]?\s*"), ""),                     # "spec B4.2 100 x ...", "Spec B4.1 quote: ..."
    (re.compile(r"\s*\(" + _TOKEN + r"\)"), ""),                                           # "assumed (U)", "Estimate (U): ..."
    (re.compile(r"\(" + _TOKEN + r"\s*[:;,]\s*"), "("),                                     # "(U: cite ...)", "(V: 28-day ...)", "(U, 300-600 mm)"
    (re.compile(r"\(" + _TOKEN + r"\s+(?=[a-z])"), "("),                                   # "(V avg: 50% planted ...)", "(V month)"
    (re.compile(r"[,;]\s*" + _TOKEN + r"\)"), ")"),                                         # "(rule of thumb, U)"
    (re.compile(r"\s*\(?\bB\d+\.\d+\)?(?=[\s.,;:)]|$)"), ""),                       # bare section refs "for B4.10 income" (bands like B04 have no dot)
    (re.compile(r"(?<=[a-z0-9)]) U(?=[),;]|\.(?!\w)|\s|$)"), " assumed"),                             # "(drain date U)", "ratings U, range", "thresholds U)"
    (re.compile(r"(?<=[a-z0-9)]) V(?=[),;]|\.(?!\w))"), " verified"),                               # "Table 12 where V)"
    (re.compile(r"^" + _TOKEN + r"\s*[:;]?\s+"), ""),                                       # leading "U " / "U: "
]
TIDY = [(re.compile(r"\(\s*\)"), ""), (re.compile(r"\(\s+"), "("), (re.compile(r"\s+\)"), ")"), (re.compile(r"\s+([.,;:])"), r"\1"),
        (re.compile(r"([;,])\1+"), r"\1"), (re.compile(r"[ \t]{2,}"), " "), (re.compile(r"^[\s:;,]+"), "")]
_QUICK = re.compile(r"\bU\b|\bV\b|[Ss]pec B\d|\bB\d+\.\d")


def clean_text(s: str) -> str:
    """Strip internal markers from one user-facing string. Strings without a marker come back unchanged (same object)."""
    if not _QUICK.search(s):
        return s
    out = s
    for a, b in PHRASES:
        out = out.replace(a, b)
    for rx, rep in PATTERNS:
        out = rx.sub(rep, out)
    for rx, rep in TIDY:
        out = rx.sub(rep, out)
    out = out.strip()
    if out and s[:1].isupper() and out[:1].islower():
        out = out[0].upper() + out[1:]
    return out or s


# ---------------------------------------------------------------- links
# Repo path / internal id (regex on the url) -> public page of the dataset. First match wins.
PUBLIC_URLS = [
    (r"(?:^|/)cdec\b", "https://cdec.water.ca.gov/"),
    (r"(?:^|/)ncei\b", "https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily"),
    (r"(?:^|/)power(?:_nrt)?\b", "https://power.larc.nasa.gov/"),
    (r"(?:^|/)usdm\b", "https://droughtmonitor.unl.edu/"),
    (r"(?:^|/)cdl\b", "https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php"),
    (r"(?:^|/)s2\b", "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a"),
    (r"(?:^|/)landsat\b", "https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2"),
    (r"(?:^|/)openet\b", "https://etdata.org/"),
    (r"(?:^|/)imerg\b", "https://gpm.nasa.gov/data/imerg"),
    (r"(?:^|/)smap", "https://smap.jpl.nasa.gov/"),
    (r"(?:^|/)grace\b", "https://nasagrace.unl.edu/"),
    (r"(?:^|/)hls", "https://hls.gsfc.nasa.gov/"),
    (r"(?:^|/)modis\b", "https://modis.gsfc.nasa.gov/data/dataprod/mod13.php"),
    (r"(?:^|/)ecostress\b", "https://ecostress.jpl.nasa.gov/"),
    (r"(?:^|/)dswx\b", "https://www.jpl.nasa.gov/go/opera/products/dswx-product-suite/"),
    (r"(?:^|/)soil\b", "https://sdmdataaccess.sc.egov.usda.gov/"),
    (r"(?:^|/)eccc\b", "https://climate.weather.gc.ca/"),
]
PUBLIC_URLS = [(re.compile(rx), u) for rx, u in PUBLIC_URLS]
_REPO = re.compile(r"^(?:backend|data|docs|fixtures|frontend|schemas|apps)/|^[\w.-]+\.(?:md|json|py|parquet)(?:#|$)|^urn:fieldshift:")
_GITHUB_BLOB = re.compile(r"^https?://github\.com/[^/]+/[^/]+/(?:blob|tree)/")
_EMBEDDED = re.compile(r"https?://[^\s)\"']+")
_BARE_DOMAIN = re.compile(r"^(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:/\S*)?$", re.I)


def public_url(u: str) -> tuple[str, bool]:
    """(url to serve, internal?) for one source link."""
    if _GITHUB_BLOB.match(u):
        return u, True
    if u.startswith(("http://", "https://")):
        return u, False
    if _REPO.search(u):
        if u.startswith(("data/", "backend/")):
            m = _EMBEDDED.search(u)            # "data/cache/x/ncei.parquet (NOAA GHCN-Daily via NCEI, https://...)"
            path = u.split(" ")[0]
            for rx, pub in PUBLIC_URLS:
                if path.startswith("data/cache/") and rx.search(path.rsplit("/", 1)[-1]):
                    return pub, False
            if m:
                return m.group(0), False
        return u, True
    if _BARE_DOMAIN.match(u):
        return "https://" + u, False
    return u, False


# ---------------------------------------------------------------- walk
def sanitize(x: Any, key: str | None = None) -> Any:
    """Return a cleaned copy of a JSON payload (dicts/lists rebuilt; unchanged strings shared)."""
    if isinstance(x, dict):
        out = {}
        internal = False
        for k, v in x.items():
            if k in ("url", "source_url") and isinstance(v, str):
                v, inside = public_url(v)
                internal = internal or inside
                out[k] = v
            elif isinstance(v, str) and (k in SKIP_KEYS or k.endswith(("_id", "_url"))):
                out[k] = v
            else:
                out[k] = sanitize(v, k)
        if internal:
            out["internal"] = True
        return out
    if isinstance(x, list):
        return [sanitize(v, key) for v in x]
    if isinstance(x, str):
        return clean_text(x)
    return x
