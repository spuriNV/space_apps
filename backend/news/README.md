# backend/news: news timeline cache (spec B9)

Fetches dated headlines for six windows, ranks (gov 1 > farm press 2 > other 3), drops items with no place match, dedupes, keeps the top 12 per window, writes NewsItem lists (spec B3).

Run: `uv sync && uv run python -m news.pipeline` (cached responses in `cache/` are reused; `--refresh` refetches; GDELT calls are spaced 6 s and retried on 429). Checks: `uv run python checks/run_checks.py` (last output in `checks/last_run.txt`).

Outputs: `out/car_colusa_rice.json`, `out/caf_tulare_forage.json`, `out/bc_opener.json` (NewsItem plus underscore-prefixed helper fields `_via`, `_publisher_url`; strip them if a strict schema is needed), `out/proposed_markers.json`, `out/_stats.json`.

## Honesty notes
- `signal`: `{dataset, value_pct: null, lead_days: null}`. No satellite signal computed. `dataset` is only the planned signal (smap_l3 / imerg_daily / grace_gw).
- `date` is the publisher date from the RSS pubDate, GDELT `seendate` (date first seen, may lag publication by a day or so), or the page's own metadata (spec-cited pages).
- Google News `url` is the redirect link as returned; ranking uses the `<source url>` publisher domain in the feed. Publisher URLs were not resolved (Google serves a JS interstitial).
- Place match is a substring check of title (plus Google description, which is the title) against place terms in `news/windows.py`. For CAR I added region terms (California Rice, Sacramento River, Butte County, Sutter) because titles rarely say Colusa. GDELT matches on article body but returns only titles, so many GDELT hits are dropped (e.g. "Glenn" matched people's names).
- `car_2023_wet`: the exact spec Google query returned 0 items, so a documented relaxed query (`q_fallback` in windows.py: drops the farm* clause, adds harvest/planting) was used. Only 4 items survive; the window is thin.
- Spec-cited pages (A1) were fetched directly and dated from their own metadata: NASA Earth Observatory (2022-10-03), Water Board probation release (2024-04-15), BC Gov release 2023FOR0052-001305 (2023-08-16), Country Life in BC (2021-11-17), NBC, CBC. Those marked gov/farm are the only rank 1/2 items outside Farm Progress.
- GDELT does reach back to 2021 for these windows (returned 55-100 articles each; capped at 100). Many are off-topic.

## Blocked
- DWR news (`https://water.ca.gov/News`, `/News/News-Releases`, `/rss`): HTTP 403 (bot block). CDFA press releases (`https://www.cdfa.ca.gov/egov/Press_Releases/`): HTTP 403; `https://www.cdfa.ca.gov/rss.xml` returns HTML, not a feed.
- State Water Board year index `https://www.waterboards.ca.gov/press_room/press_releases/2024/index.html`: HTTP 200 but the list is JS-rendered (no links in the HTML); no RSS found. Only the spec-cited release was used.
- BC Gov News RSS (`https://news.gov.bc.ca/Feed`, `/ministries/agriculture-and-food/feed`): work, but each holds only the latest ~10 items (Jul-Oct 2026), so 0 items fall in the 2021/2023 windows. Gov coverage for BC comes from the spec-cited release page only.
- agalert.com spec-cited page (`.../january-3-2024/later-rice-harvest-deals-minor-yield-quality-impacts/`): date/title not parseable from the HTML; also outside the CAR 2023 window (ends 2023-11-15). Not used.
- Spec-cited Castanet link `https://www.castanetkamloops.net/news/Salmon-Arm/571142/` now serves "Salmon Arm News archive page 236", not the article. Not used.
- GDELT returned `HTTP 429 "Please limit requests to one every 5 seconds"` on first attempts when run too fast; resolved by 6 s spacing plus retry.
- Link spot-check: abc10.com returns HTTP 403 and appeal-democrat.com HTTP 429 to a plain script (bot blocks, not necessarily dead links); Google News redirect URLs return HTTP 200 (interstitial), which does not prove the publisher page loads. These are reported as FAIL/INFO by the checker, not dropped.
