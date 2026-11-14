"""Fetch (cached), rank, dedupe, write out/*.json. Run: uv run python -m news.pipeline [--refresh]"""
import hashlib, json, re, sys, time, html
from datetime import datetime, date
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote, urlparse
import xml.etree.ElementTree as ET
import httpx
from .windows import WINDOWS, OUTPUT, CITED, GOV, FARM

ROOT = Path(__file__).resolve().parent.parent
CACHE, OUT = ROOT / "cache", ROOT / "out"
UA = {"User-Agent": "Mozilla/5.0 (Field Shift hackathon news cache)"}
TOP_N = 12
BLOCKED: list[str] = []
_last_gdelt = [0.0]


def cached_get(name: str, url: str, params=None, gdelt=False, refresh=False):
    """Return (status, text); cache body under cache/<name>. Errors are cached as .err and logged."""
    p = CACHE / name
    if p.exists() and not refresh:
        return 200, p.read_text()
    last = None
    for attempt in range(6 if gdelt else 2):
        if gdelt:
            wait = 6 - (time.time() - _last_gdelt[0])
            if wait > 0: time.sleep(wait)
            _last_gdelt[0] = time.time()
        try:
            r = httpx.get(url, params=params, headers=UA, timeout=30, follow_redirects=True)
        except Exception as e:
            last = f"{type(e).__name__}: {e}"; time.sleep(3); continue
        if r.status_code == 200 and not (gdelt and not r.text.lstrip().startswith("{")):
            p.write_text(r.text); return 200, r.text
        last = f"HTTP {r.status_code} {r.text[:150]!r}"
        time.sleep(15 if r.status_code == 429 else 3)
    BLOCKED.append(f"{url} params={params}: {last}")
    return 0, last


def domain(u: str) -> str:
    return (urlparse(u).hostname or "").removeprefix("www.")


def rank_of(u: str) -> int:
    d = domain(u)
    if any(d == g or d.endswith("." + g) for g in GOV): return 1
    if any(d == f or d.endswith("." + f) for f in FARM): return 2
    return 3


def norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def google(wid, w, refresh, key="q", suffix=""):
    q = f'{w[key]} after:{w["start"]} before:{w["end"]}'
    st, txt = cached_get(f"google_{wid}{suffix}.xml", "https://news.google.com/rss/search",
                         {"q": q, "hl": w["hl"], "gl": w["gl"], "ceid": w["ceid"]}, refresh=refresh)
    items = []
    if st != 200: return items
    for it in ET.fromstring(txt).iter("item"):
        src = it.find("source")
        title = html.unescape(it.findtext("title", ""))
        sname = src.text if src is not None else ""
        if sname and title.endswith(" - " + sname): title = title[: -len(sname) - 3]
        d = parsedate_to_datetime(it.findtext("pubDate")).date().isoformat()
        items.append(dict(date=d, title=title, source=sname, link=it.findtext("link"),
                          pub_url=src.get("url") if src is not None else "",
                          text=title + " " + html.unescape(re.sub("<[^>]+>", " ", it.findtext("description", ""))),
                          via="google_news" if not suffix else "google_news_fallback"))
    return items


def gdelt(wid, w, refresh):
    s, e = w["start"].replace("-", ""), w["end"].replace("-", "")
    st, txt = cached_get(f"gdelt_{wid}.json", "https://api.gdeltproject.org/api/v2/doc/doc",
                         {"query": w["gdelt"], "mode": "artlist", "format": "json", "maxrecords": 100,
                          "startdatetime": s + "000000", "enddatetime": e + "235959"}, gdelt=True, refresh=refresh)
    items = []
    if st != 200: return items
    for a in json.loads(txt).get("articles", []):
        d = datetime.strptime(a["seendate"][:8], "%Y%m%d").date().isoformat()
        items.append(dict(date=d, title=" ".join(a["title"].split()), source=a.get("domain", ""), link=a["url"],
                          pub_url=a["url"], text=a["title"], via="gdelt"))
    return items


def bc_feeds(wid, w, refresh):
    items = []
    for nm, u in [("bc_all", "https://news.gov.bc.ca/Feed"), ("bc_agri", "https://news.gov.bc.ca/ministries/agriculture-and-food/feed")]:
        st, txt = cached_get(f"{nm}.xml", u, refresh=refresh)
        if st != 200: continue
        for it in ET.fromstring(txt.lstrip("﻿")).iter("item"):
            d = parsedate_to_datetime(it.findtext("pubDate")).date().isoformat()
            t = html.unescape(it.findtext("title", ""))
            items.append(dict(date=d, title=t, source="BC Gov News", link=it.findtext("link"), pub_url=it.findtext("link"),
                              text=t + " " + html.unescape(re.sub("<[^>]+>", " ", it.findtext("description", ""))), via="bc_gov_rss"))
    return items


META = [r'property="article:published_time" content="([^"]+)"', r'"datePublished"\s*:\s*"([^"]+)"',
        r'name="DC\.date\.issued" content="([^"]+)"', r'<time[^>]*datetime="([^"]+)"', r'<p>(20\d\d-\d\d-\d\d)</p>', r'Posted: (\w+ \d+, \d{4})']
TITLE = [r'property="og:title" content="([^"]+)"', r"<title>([^<]+)</title>"]


def cited(wid, w, refresh):
    items = []
    for u in CITED.get(wid, []):
        st, txt = cached_get("cited_" + hashlib.md5(u.encode()).hexdigest()[:10] + ".html", u, refresh=refresh)
        if st != 200: continue
        d = next((m.group(1) for pat in META if (m := re.search(pat, txt))), None)
        if d and re.match(r"[A-Za-z]", d): d = datetime.strptime(d, "%B %d, %Y").date().isoformat()
        elif d: d = d[:10]
        t = next((html.unescape(m.group(1)).strip() for pat in TITLE if (m := re.search(pat, txt))), None)
        if not d or not t:
            BLOCKED.append(f"{u}: could not parse date/title from page"); continue
        t = re.sub(r"\s*\|\s*California State Water Resources Control Board$", "", t)
        items.append(dict(date=d, title=t, source=domain(u), link=u, pub_url=u, text=txt[:200000], via="spec_cited_page"))
    return items


def build(refresh=False):
    CACHE.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
    stats, final = {}, {}
    for wid, w in WINDOWS.items():
        raw = google(wid, w, refresh)
        if "q_fallback" in w and not raw: raw = google(wid, w, refresh, "q_fallback", "_fallback")
        raw = raw + gdelt(wid, w, refresh) + cited(wid, w, refresh)
        if w["preset"] == "bc_opener": raw += bc_feeds(wid, w, refresh)
        stats[wid] = {"fetched": {}, "in_window": 0, "place_match": 0, "kept": 0}
        for r in raw: stats[wid]["fetched"][r["via"]] = stats[wid]["fetched"].get(r["via"], 0) + 1
        inw = [r for r in raw if w["start"] <= r["date"] <= w["end"]]
        stats[wid]["in_window"] = len(inw)
        out, seen_t, seen_u = [], set(), set()
        for r in inw:
            hay = r["text"].lower()
            pm = [p for p in w["place"] if p in hay]
            if not pm: continue
            r["place_match"] = [p.title() if p != "glenn-colusa" else "Glenn-Colusa" for p in pm]
            r["rank"] = rank_of(r["pub_url"] or r["link"])
            out.append(r)
        stats[wid]["place_match"] = len(out)
        out.sort(key=lambda r: (r["rank"], r["date"], r["title"]))
        keep = []
        for r in out:  # dedupe by publisher url / normalized title
            k = norm(r["title"])
            u = (r["pub_url"] if not r["via"].startswith("google") else r["link"]).split("?")[0]
            if k in seen_t or u in seen_u: continue
            seen_t.add(k); seen_u.add(u); keep.append(r)
        keep = keep[:TOP_N]
        stats[wid]["kept"] = len(keep)
        stats[wid]["kept_by_via"] = {v: sum(1 for r in keep if r["via"] == v) for v in {r["via"] for r in keep}}
        final[wid] = [dict(date=r["date"], title=r["title"], source=r["source"], url=r["link"], rank=r["rank"],
                           place_match=r["place_match"], query_id=wid,
                           signal=dict(dataset=w["dataset"], value_pct=None, lead_days=None),
                           _via=r["via"], _publisher_url=r["pub_url"]) for r in keep]
    for preset, wids in OUTPUT.items():
        items = sorted([i for wid in wids for i in final[wid]], key=lambda i: (i["query_id"], i["rank"], i["date"]))
        (OUT / f"{preset}.json").write_text(json.dumps(items, indent=2, ensure_ascii=False))
    (OUT / "_stats.json").write_text(json.dumps({"stats": stats, "blocked": BLOCKED}, indent=2))
    print(json.dumps(stats, indent=1)); print("BLOCKED:", *BLOCKED, sep="\n  ")


if __name__ == "__main__":
    build("--refresh" in sys.argv)
