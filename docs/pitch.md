# CropLytics: pitch, slides and video

NASA Space Apps 2026, Vancouver. Challenge: **Field Shift: Adapting Farms with NASA Data**.
Submission: the 7 slides in `docs/slides/index.html` (or the 30-second video), due Sunday 23:59, plus a 3-minute live pitch.

Written 14 Nov 2026 from the repo as it stands. Every number below is in the source table at the end, with the file it comes from. Every item in `docs/critical-review.md` section 5 ("Claims we must not make") is respected; the ones closest to the script are listed under "Words to avoid".

Screenshots are referenced by filename only (`design/screenshots/app/<name>.png`, copied to `docs/slides/img/<name>.png`). When they are refreshed, copy the new files over the old ones with the same names; the slides pick them up.

---

## 1. Three-minute script

Spoken lines are in quotes. **Speaker** talks, **Driver** clicks the app. About 417 spoken words. At a steady 145 words a minute that is 2:53, which leaves about 7 seconds for clicks and pauses, so the Driver clicks while the Speaker is still finishing the previous line.

### 0:00–0:30 BC opener (slides 1 and 2; Speaker)

*Slide 1 (title, ISS photo) is up as you start. Move to slide 2 on "Two years earlier".*

> "On the sixteenth of August 2023, about 398 licence holders on BC's lower Salmon River were ordered to stop irrigating forage, mid-season. Two years earlier, Sumas Prairie went under water.
> NASA's satellites see these fields. What BC lacks is the ground data to prove a tool works: no measured water use field by field, and a short crop-map record. So we built it, and checked it, where the data is rich: California."

(72 words)

### 0:30–0:45 Pick the field (app, overview; Driver)

*Driver switches to the app, already open on the overview (`overview.png`). Click the card **"Rice field 4 miles east of Williams"**.*

> "This is a real 149-acre rice field in Colusa County. CropLytics answers three questions a grower asks: what is happening on my field, what is likely this winter, and what would a different rotation cost me."

(37 words)

### 0:45–1:15 What happened in 2022 (app, "This field's year"; Driver)

*Click **"This field's year"** in the field panel (`year.png`), then **"Show earlier years (2016–2022)"** under the strips. Point at the 2022 strip.*

> "Each strip is one year, seen by NASA's harmonised Landsat and Sentinel-2 imagery: green is crop, brown is bare, blue is flooded. Here is 2022: brown nearly all year, never green. Water ran short across the valley, and this field was fallowed, like most of the county. Colusa planted 126,500 acres of rice in 2020 and 20,600 in 2022. Crop insurance paid out 146 million dollars on Colusa rice that year."

(71 words)

### 1:15–1:45 This winter's outlook (app, "Coming season"; Driver)

*Click **"Coming season"** in the left rail (`coming-season.png`). Point at the rain outlook, then the Shasta line and the allocation table (the 2021 row), then "Longest bare stretch this winter".*

> "Now this winter. NOAA's outlook leans wetter than normal: a 50% chance of above-normal rain for January to March. It's an outlook, not a forecast. Shasta is 49% full. In mid-November 2021 it was 24%, and the next year settlement contractors got 18% of their water. This field is usually bare from mid-February to early April, and in 54% of past winters a one-inch rain day landed in that window."

(70 words)

### 1:45–2:15 Compare, and the validation line (app, "Compare"; Driver)

*Click **"Compare rotations"** (or **Compare** in the rail), then the **"Dry-year safflower"** card (`compare.png`). Point at "You gain", then "You give up", then the "Water against your limit" box on the right.*

> "If water comes in low next year, what does a switch cost? Dry-year safflower needs about 2 acre-feet of irrigation per acre instead of about 5 for rice, and that 2 is an upper bound. You give up ground cover: more bare soil when heavy rain arrives.
> Are the water numbers right? On the years this field grew rice, our model runs 16% above OpenET's satellite-based water use; on our alfalfa field, 21%. We tuned nothing. So it errs high: conservative about water."

(83 words)

### 2:15–2:30 The brief (app, "Print"; Driver)

*Click **"Print for your adviser"** (`brief.png`). Scroll once to "Check locally before anything is seeded".*

> "And one page for the adviser: the field, the outlook, the option, what it gains and gives up, and what to check locally before anything is seeded."

(27 words)

### 2:30–3:00 Close (slide 7; Speaker)

*Driver switches back to the slides, slide 7.*

> "CropLytics supports the grower and the adviser; it doesn't replace them. Every number is sourced or marked as our assumption. It runs on two fields today, and some NASA layers aren't in yet. The next step is home: a BC field, with a measured water check, before we'd show it to a BC farmer. Thank you."

(57 words)

**Total spoken: about 417 words, about 2:53 at 145 words a minute, 3:00 with clicks.** If a rehearsal runs long, cut in this order: the insurance sentence (0:45 section, 12 words), then the 2021 Shasta comparison (1:15 section, 19 words). Never cut "and that 2 is an upper bound" or "We tuned nothing"; they are the caveats that keep the claims honest.

### Words to avoid on stage

| Do not say | Say instead | Why (critical-review.md §5) |
|---|---|---|
| "validated", "accurate to 16%" | "runs 16% above OpenET; we tuned nothing" | It is a one-sided overestimate on the baseline only, against another estimate |
| "saves 3.4 acre-feet" | "about 2 instead of about 5, and that 2 is an upper bound" | Typical-year model difference; no stored soil water counted |
| "OpenET checked the safflower / irrigation numbers" | Say OpenET checked today's crop only | Alternatives were never grown there |
| "our AI is 99% accurate" | "on the 2022 drought year, 83% against 78% for the simple rule, at Kings" | Colusa labels are rule-made |
| "uses SMAP, MODIS, ECOSTRESS" | name only what the screens show: HLS, GRACE-FO, GPM IMERG, NASA POWER | SMAP, MODIS and ECOSTRESS say "not downloaded yet" in the 16:02 screenshots; recheck on the day |
| "forecast", "real-time" | "outlook, not a forecast" | CPC outlooks; calendar data has gaps |
| "the 2023 floods hit this field" | Say nothing about 2023 at this field | No water weeks in the 2023 crop season |
| "BC has no data" | "BC lacks field-scale measured water use and a long crop-map record" | Overclaim |
| "works for any farm" | "two fields today" | Two hand-set-up fields |
| "84% drop in planting" | the two acreage numbers (126,500 and 20,600) | Avoids two different "drop" figures |
| a bare-day count ("85 more days") | "more bare soil" | Screens disagree on bare days (§2 item 5) |
| a water-limit verdict ("over your limit") | skip it | The default limit is an example and may change tonight |

---

## 2. Seven-slide outline

Built as `docs/slides/index.html`. Arrow keys move; Print (Cmd+P, landscape, no margins, background graphics on) gives a 7-page PDF.

**1. Title**
- Headline: **CropLytics**: plan next season's rotation with NASA Earth data.
- A crop-rotation planner for a grower and their farm adviser. NASA Space Apps 2026, Vancouver.
- Challenge: Field Shift: Adapting Farms with NASA Data.
- Image: ISS astronaut photo of the Sacramento Valley near Colusa, 4 Mar 2020 (`img/iss-sacramento-valley.jpg`, from `data/cache/car_colusa_rice/iss/ISS062-E-81144.jpg`), with NASA's credit line.

**2. The BC problem and the data gap**
- Headline: BC farms are living the extremes, but there's no ground data to prove a tool works.
- 16 Aug 2023: about 398 licence holders on the lower Salmon River and Bessette Creek were told to stop irrigating forage. Nov 2021: the Sumas Prairie flood.
- BC lacks field-scale measured crop water use (OpenET doesn't cover Canada) and has crop maps only from 2011.
- Figure: typographic; two dated events and a "has / lacks" list. No screenshot.

**3. Built where the data is rich**
- Headline: So we built it where we can check it: two real California fields.
- A 149-acre rice field 4 miles east of Williams (Colusa County) and a 73-acre alfalfa field 6.5 miles south of Hanford (Kings County).
- NASA HLS (harmonised Landsat and Sentinel-2), NASA POWER (sunlight, humidity, wind), GPM IMERG rain, GRACE-FO soil moisture and groundwater, NASADEM and ISS photos; checked against OpenET, NOAA stations and USDA records. SMAP, MODIS and ECOSTRESS: not in yet.
- Screenshot: `overview.png`.

**4. What the grower sees**
- Headline: The grower sees their own field in inches, acre-feet and days.
- Your field now; this field's year (bare, green or flooded, since 2016); coming season (NOAA outlook, reservoirs, allocations, the bare window).
- 2022 at this field: fallow. Colusa planted 126,500 acres of rice in 2020 and 20,600 in 2022.
- Screenshots: `year.png` (large), `field-now.png`, `coming-season.png`.

**5. How we know it's right**
- Headline: We checked it against data we didn't use to build it.
- Water: our model runs 16% (rice) and 21% (alfalfa) above OpenET on the years each crop was grown; nothing tuned.
- Rule vs machine learning on the 2022 drought year (Kings): 78% vs 83%, below our 85% target. Satellite weather model vs stations: 51 vs 12–30 days at or above 104 °F at Colusa in 2022, so temperature comes from stations.
- Figure: three small bar charts (inline SVG in the deck).

**6. Compare and brief**
- Headline: Compare a switch in acre-feet, then print one page for the adviser.
- Gain and give up against today, with ranges; overlapping ranges are called "no clear difference".
- Dry-year safflower: about 2 acre-ft/acre of irrigation against about 5 for rice (the 2 is an upper bound). Round numbers on purpose: the screens show 1.9 and 5.2 today, and they move with the weather case and any engine fix. The page ends with what to check locally before seeding.
- Screenshots: `compare.png`, `brief.png`.

**7. Limits and the next step to BC**
- Headline: What it can't do yet, and the road back to BC.
- Two fields set up by hand. SMAP, MODIS and ECOSTRESS are not downloaded yet; GRACE-FO groundwater is a basin-wide signal, not the grower's own well. Market and income are not counted yet. Water is well-watered demand, so it runs high.
- Next: a BC field, with a measured water check and a longer crop record, before a BC farmer sees it. Supports the grower and adviser; never replaces them.
- Screenshot: `drilldown-3d.png` (crop, then root-zone soil moisture and groundwater, each layer with its source and scale).

---

## 3. Thirty-second video

1920×1080, captions burned in, voice-over about 77 words. Record the app at 1440×900 and scale up; use the slide deck for the cards.

| Time | Picture | Voice-over | On-screen text |
|---|---|---|---|
| 0:00–0:04 | ISS photo of the Sacramento Valley, slow push-in (slide 1 image) | "In August 2023, BC told about 398 licence holders to stop irrigating forage." | 16 Aug 2023 · Salmon River, BC |
| 0:04–0:09 | Slide 2, the "has / lacks" list | "BC lacks the ground data to prove a tool works, so we built it in California." | Built in California, checked there first |
| 0:09–0:15 | Screen recording: "This field's year", earlier years open, cursor on 2022 | "A Colusa rice field from NASA's Landsat and Sentinel-2 imagery: fallow in the 2022 drought." | 2022: no rice |
| 0:15–0:20 | Screen recording: "Coming season", rain outlook and Shasta | "This winter's outlook, reservoirs and allocations, in one place." | Outlook, not a forecast |
| 0:20–0:25 | Screen recording: Compare, "Dry-year safflower" | "What a switch gains and gives up. Our water model runs 16 to 21% above OpenET." | Checked against OpenET: runs 16–21% high |
| 0:25–0:30 | Brief slides in; end card (slide 7 closing line, team, event) | "One page for the adviser. Next stop: BC." | CropLytics · NASA Space Apps 2026, Vancouver |

Voice-over: 77 words, a brisk but clear read for 30 seconds. Keep the music low or leave it out; captions carry it on mute.

---

## 4. Demo safety

**Roles**
- **Speaker:** opener, close and all voice during the demo. Never touches the laptop.
- **Driver:** the only person clicking. Runs the click path in section 1 exactly; does not explore.
- **Timekeeper:** holds a phone stopwatch, signals at 0:30, 1:45 and 2:30, and has the backup video open and paused on a second laptop.

**Before going up (Driver, 10 minutes before)**
1. `cd backend/api && uv run uvicorn app.main:app --port 8000` (serves the built app and the saved data; no keys needed). Open the app, pick the Colusa field once so map tiles cache, then return to the overview.
2. Check the top-right indicator. If it says "Example data only", the API isn't reaching the data: go to fallback 2 straight away.
3. Open `docs/slides/index.html` in a second browser window, on slide 1. Fonts are embedded, so it works offline.
4. Laptop: do not disturb on, notifications off, screen sleep off, zoom 100%, window 1440×900 or larger, charger in.

**Fallback 1: backup recording.** Record the full click path (0:30 to 2:30 of the script) as a screen capture tonight after the screenshots are refreshed, at 1440×900, no audio. Keep it on both laptops and a USB stick, not in git (too large). If the live app stalls for more than 5 seconds, Timekeeper starts the video and Speaker keeps talking over it; same words, same order.

**Fallback 2: offline, no internet.** The satellite basemap needs internet; the field data doesn't. If the venue Wi-Fi is down, use a phone hotspot first. If that fails, skip the app and present slides 3 to 6, which carry the same screens; the script lines stay the same, with "Here is" pointing at the screenshots.

**Fallback 3: projector or laptop failure.** Print the deck to PDF tonight (7 pages) and keep it on a USB stick and a phone. Speaker can give the full pitch from the PDF.

**Rehearse three times** against the stopwatch, at least once from the backup video and once from slides only.

---

## 5. One line per judge

From `docs/judges.md` (matches are best guesses).

| Judge | What they'll look for | Where the pitch answers it |
|---|---|---|
| Amr Marzouk (mechatronics, P.Eng.) | Does it run, and is the engineering sound and checked? | Live demo; slide 5's three checks; "we tuned nothing to match" (1:45) |
| Shahbano Farooq (HCI) | Can a grower read it without training? | Click path in grower words (0:30–2:30); slides 4 and 6: inches, acre-feet, days, plain questions |
| Sohan Seemakurthy (ag data, entrepreneur) | Who uses it, how big the problem is, what's next | $146M Colusa rice insurance payout in 2022 (0:45 section); slide 3's two fields; slide 7's next step |
| Dawn Zheng (physics, CSA internship) | Real use of space data and honesty about its limits | Slide 3's NASA data list; slide 5's satellite-vs-station chart; slide 7 says what isn't in yet (SMAP, MODIS, ECOSTRESS) and that groundwater is basin-wide |
| Ebrahim Al-Yousefi (communications) | A clear human story and community impact | The BC opener (0:00) and the close back to BC (2:30) |

The critical review also mentions NASA reviewers (an ML judge and ISS-photo specialists) for the global round. For them: slide 5's rule-vs-ML line with its caveat, and slide 1's ISS photo with NASA's credit line.

---

## 6. Where every number comes from

| Number | Used in | Source file |
|---|---|---|
| 16 Aug 2023; about 398 licence holders; lower Salmon River and Bessette Creek; stop irrigating forage | Opener, slide 2, video | `docs/research-findings.md` §1 and `docs/field-shift-plan.md` §2 (BC release 2023FOR0052-001305; plan §7 says confirm before pitching) |
| Nov 2021 Sumas Prairie flood | Opener, slide 2 | `docs/research-findings.md` §1 |
| BC: no OpenET field water use; crop maps only from 2011 | Opener, slide 2 | `docs/field-shift-plan.md` §2 ("BC's data gap"); `docs/critical-review.md` §5 |
| 149 acres, 4 miles east of Williams, Colusa County | 0:30, slide 3 | App field panel (`field-now.png`, `drilldown-3d.png`) |
| 73 acres, 6.5 miles south of Hanford, Kings County | Slide 3 | App field picker (`overview.png`) |
| Field fallow in 2022 (also 2016, 2020); 2022 strip brown nearly all year (297 bare, 34 thin, 34 flooded, 0 crop days) | 0:45, slide 4 | `backend/field/out/car_colusa_rice/crop_history.json` (USDA Cropland Data Layer); `backend/field/out/car_colusa_rice/calendar.json` → `years[2022].summary` |
| Colusa rice planted 126,500 acres (2020), 20,600 (2022) | 0:45, slide 4 | `data/cache/car_colusa_rice/nass.parquet` (USDA NASS survey, "RICE - ACRES PLANTED") |
| $145.6M Colusa rice insurance payout in 2022; $247.8M 2010–2024; 84% for failed irrigation supply | 0:45, slide 2 notes | `backend/ground/out/car_colusa_rice/rma_profile.json` (USDA RMA cause of loss) |
| Rain outlook: 50% above normal Jan–Mar, 40% Dec–Feb (CPC, issued 15 Oct 2026) | 1:15 | `backend/outlook/out/car_colusa_rice/outlook.json` → `cpc_seasonal_outlook` |
| Shasta 49% full, 92% of average for 13 Nov | 1:15 | same file → `reservoirs_now.SHA` |
| Shasta 24% full mid-Nov 2021; 2022 settlement contractors 18% | 1:15 | same file → `allocations_context.storage_vs_final_allocation.rows` |
| Usually bare mid-Feb to early Apr (median 48.5 days, 18–79) | 1:15 | same file → `field_expectations_from_history.bare_window` |
| 54% of past winters (1981–2024) had a 1-inch rain day in that window | 1:15 | same file → `heavy_rain_in_window.chance_any_day_ge_25mm_climatology` (53.7%) |
| Irrigation need: rice + winter flood 5.2, dry-year safflower 1.9 acre-ft/acre | 1:45, slide 6 | same file → `irrigation_2027.strategies`; safflower is an upper bound per `backend/engine/README.md` ("Sanity") |
| +16% rice (1280 vs 1108 mm/yr), +21% alfalfa (1343 vs 1112), CDL-matched years, never tuned | 1:45, slide 5, video | `backend/engine/README.md`, "Validation against OpenET", row C3 |
| Kings 2022 hold-out: rule 78%, random forest 83%, target 85%; Colusa 99% caveat | Slide 5 | `backend/ai/README.md`, "Results" and "What the numbers mean" |
| Colusa 2022 days ≥ 40 °C (104 °F): NASA POWER 51; stations 12, 14, 30 | Slide 5 | `backend/regional/README.md`, "Cross-check: POWER >= 40 C days vs NCEI stations" |
| ISS photo ISS062-E-81144, 4 Mar 2020, and credit line | Slide 1 | `data/cache/car_colusa_rice/iss/iss.json`; credit per `backend/nasa_open/README.md` §3 |

### Numbers we wanted but couldn't source from the repo
- How many California growers or acres the tool could serve statewide (only county NASS rows are cached). Colusa's own 137,000 planted acres in 2025 (`nass.parquet`) is the closest sourced number; not used on stage.
- How many BC forage farms or acres the 2023 orders affected, beyond the 398 licence count.
- The hay price jump ($75 to $190 a bale) is in `docs/research-findings.md` but marked "verify"; not used.
- How many days before the 2023 BC order the satellites showed drying (lead time). Never computed (`docs/research-findings.md` says so).
- NASA Earth Observatory's "84% drop" for Colusa rice planting: the exact year pair isn't in the repo, so the script quotes the NASS acreages instead.
- Any grower or adviser feedback: nobody outside the team has used the app yet.

### Update before Sunday if tonight's fixes land
- GRACE-FO soil moisture and groundwater and GPM IMERG rain went live in the 16:02 screenshots, and the year view now credits NASA HLS; slides 3 and 7 and the script already say so. If SMAP, MODIS or ECOSTRESS land too, add them to slide 3 and drop them from slide 7.
- The machine-learning strip is now in the app ("Compare with machine learning" on "This field's year", refreshed screenshots, 14 Nov evening). If a rehearsal has 5 seconds spare at 0:45, click it and say: "Machine learning gives a second opinion, not the answer." Otherwise leave it to slide 5.
- The field picker already reads "Rice in 7 of the last 10 years; left fallow 2016, 2020 and 2022", matching the crop maps.
- Field names changed to "4 miles east of Williams" and "6.5 miles south of Hanford" in the refreshed screenshots; the script and slides use the new names. If they change again, update the click target at 0:30 and slide 3.
