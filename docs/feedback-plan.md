# Mentor feedback plan (15 Nov 2026)

Plan only; nothing built. Item 3 (the BC example field) is with another agent. Checked against `origin/main` (62 of 64 commits are Caiden's; no Saketh commits and no recent removals yet). Features already cut earlier, so none of this touches them: the bottom timeline, story mode in the app, the theme switcher, the 3D water-use mode. Everything below lands on screens that still exist: pick list, Field now, Coming season, This field's year, Compare, Print. Re-check `git log origin/main` before building.

**Clock check.** `PLAN.md` says feature freeze Saturday 22:00 and submission Sunday 23:59. Today is Sunday 15 Nov. If the deadline stands, ship items 2, 1 and 5 (all front-end only) and treat item 4 as post-submission or a cut-down version.

| # | Item | Fits? | Effort | Order |
|---|---|---|---|---|
| 2 | Less text | Yes | S | 1st |
| 1 | Larger fonts | Yes | M | 2nd |
| 5 | Soil composition | Yes | S | 3rd |
| 4 | Chat bot | Yes, with guardrails | L | 4th |

Order: cut words first (so the bigger type still fits), then the type scale, then the soil row (it uses the new scale), then the chat bot (largest, needs a key and a backend route).

---

## 2. Less text (S)

**Fit.** Validity (usability, rubric gap 5: "usability is unproven") and Presentation (a 3-minute demo and a 30-second video are read from a distance). The skill's 10-second test already says this; the screens still break it by repeating the same fact in a headline, a sentence and a note.

**Rule.** One fact once. A number gets its unit and nothing else. Hints and sources go behind More detail. No sentence over about 12 words in the farmer default.

**Cuts, screen by screen** (strings from `ui/FieldNow.tsx`, `ui/Options.tsx`, `season/ComingSeason.tsx`, `compare/ComparePanel.tsx`, `brief/RotationBrief.tsx`, `MapView.tsx`):

| Screen | Now | Replace with |
|---|---|---|
| Pick list intro | "What is happening on it now, what this winter may bring, and what another rotation would cost in water." | "Pick a field." |
| Field now intro | "Today, mid Nov 2026. Pick another date under "Viewing" to look back." | Delete (the top bar already says Viewing). |
| Meter notes | "62% of normal · line = normal"; "limit 5.0 (example) · line = limit"; "0 to 1, late Oct 2026 · line = full canopy" | "62% of normal"; "Limit 5.0 (example)"; "Late Oct 2026" |
| Soil meter note | "soil 48th, groundwater 53rd; 50 is normal" | "Soil 48th, groundwater 53rd" (the line on the bar says 50 is normal) |
| Rain answer | "1.9 inches 1 Oct to 13 Nov; normal is 3.0 inches (62% of normal)." | "1.9 in since 1 Oct. Normal: 3.0 in." |
| Action buttons | Title plus subtitle ("Rain, drought, reservoirs, bare weeks") | Title only: "What's likely this winter". |
| Soil/groundwater source line | "Soil: NASA GRACE-FO with a land model, root zone, one reading for a 17-mile square..." | Move fully to the Sources sheet; the answer keeps only "NASA GRACE-FO". |
| Map labels | "Groundwater (NASA GRACE-FO): one reading for this 17-mile square; the satellites sense about 190 miles" and "Soil moisture (NASA SMAP): one reading covers this square (6 miles across)" | "Groundwater: this 17-mile square" and "Soil moisture: this 6-mile square" |
| Coming season lede | "NOAA's outlook leans wetter than normal this winter. Outlooks, not forecasts: they tilt the odds, they don't say what will happen." | "Wetter than normal this winter. An outlook, not a forecast." |
| Winter rain note | "NOAA 3-month outlooks, the odds, not a promise." | Delete (repeats the lede). |
| Water supply | "Shasta is at 92% of average for the date. This year's federal allocation for Sacramento River settlement contractors was 100%." | "Shasta: 92% of average. Your allocation: 100%." |
| Next season | "About 5.2 acre-feet per acre; your limit is 5.0 (an example, change it on Compare). About 0.2 short." | "Needs 5.2 acre-ft/acre. Limit 5.0 (example). 0.2 short." |
| More detail teasers | "Month-by-month outlooks, drought, reservoirs, allocation history, snowpack, bare stretch, every rotation" | "Outlooks, reservoirs, every rotation" (same pattern on every screen: three words max) |
| Compare header paragraph | "Dry-year safflower against what you do now (rice + winter flood): you'd gain needs less irrigation water, about 3.3 acre-ft/acre less a year (39 in). You'd give up field bare more days, about 145 more days a year." | Delete the paragraph; the Gain / Give up columns say it. Title: "Dry-year safflower vs rice today". |
| Water against limit | "Fits your limit: needs 1.9 acre-ft/acre (likely 1.5-2.5) (typical year); today needs 5.2. An upper bound: soil water stored over winter is not counted." | "Needs 1.9 acre-ft/acre. Your limit: 5.0." Range and upper-bound note move to More detail. |
| Compare More detail | "All rotations, soil and feed scores, your priorities and what-ifs" | "All rotations and what-ifs" |
| Brief, water paragraph | "Irrigation need about X ... (likely a-b), against N ... An upper bound: soil water stored over winter is not counted, so a dry-farmed or one-irrigation crop can need much less. ... In a dry year like 2022: ..; a wet year like 2023: .." | Keep need, limit and "fits / over". Move the upper-bound sentence to a footnote; keep only the 2022 figure. |

Not reviewed line by line: This field's year (`year/YearSheet.tsx`); apply the same rule when editing. The `cite` lines are already behind More detail; leave them.

---

## 1. Larger fonts (M)

**Fit.** Validity (usability and accessibility) and Impact (growers are often older and on a phone in a truck). It also makes the stage demo and video legible. Current type is 13 px body, 11 to 12.5 px secondary, 10 to 11.5 px sources (about 80 declarations at 11.5 px or smaller in `styles.css`). Small print is carrying real content.

**New scale** (CSS tokens at the top of `frontend/app/src/styles.css`; replace the ~15 literal sizes with these):

| Token | Now | New | Used for |
|---|---|---|---|
| `--fs-fine` (floor) | 8.5 to 11.5 px | **13 px** | source lines, chart ticks, map scale, legend |
| `--fs-small` | 12 to 12.5 px | **14.5 px** | labels, meter notes, secondary lines |
| `--fs-body` | 13 to 14.5 px | **16 px** | body, rows, buttons, tabs |
| `--fs-answer` | 15 to 17 px | **20 px** (Zilla Slab 600) | the answer sentence, option names |
| `--fs-head` | 17 px | **22 px** | section and sheet headings |
| `--fs-title` | 23 px | **28 px** | field name in the panel, sheet titles, wordmark |

**Minimum: 13 px, nothing smaller, including SVG chart text and map labels.** Body at 16 px also stops iOS zooming on inputs.

**Screens that change:**
- **All:** top bar (tabs 16 px, field switcher name 18 px), map layers menu, Viewing menu, Sources sheet.
- **Field now:** panel widens from about 404 px to 460 px (max 46 vw); the 2x2 meter grid stays 2 columns, but notes wrap. Answers go to 20 px, so the text cuts in item 2 have to land first.
- **Compare:** three columns become two below 1280 px wide (Gain, Give up; water limit moves under).
- **Coming season:** the three summary cells stack below 1180 px.
- **Phone:** body 16 px already needed there; bottom-sheet peek height grows with it.
- **Print brief:** untouched (print units, one Letter page); only check it still fits.
- Native apps (`apps/android`, `apps/ios`) follow system text size; no change.

**Update** `.claude/skills/fieldshift-visual-design/SKILL.md` section 6 ("13px body, 12-12.5px secondary, 11.5px source lines, 15-17px answers") and re-shoot `design/screenshots/app/` with `node design/tools/shoot-app.mjs`.

---

## 5. Soil composition (S)

**Did we talk about it?** Partly. `PLAN.md` lists "soil type, drainage and salinity" under Field now, and the data is there, but the farmer default hides it: it is four text rows ("Soil / Holds / Drainage / Salt", `AboutField` in `ui/shared.tsx`) behind More detail, and nothing shows sand, silt and clay.

**What we already have** (SSURGO via Soil Data Access, in `data/cache/<id>/soil.json` for all 14 fields, served as `soil` by `GET /api/locations/{id}`): texture class, sand/silt/clay % (0 to 100 cm), water held (mm/m, with low and high), organic matter %, drainage class, hydrologic group, salinity (EC, dS/m). No new API route and no new fetch for California. Two contrasting real examples:

| | Colusa rice (Capay clay loam) | Kings alfalfa (Kimberlina sandy loam) |
|---|---|---|
| Sand / silt / clay | 29 / 33 / 39 % | 70 / 17 / 14 % |
| Water held | 2.1 in per foot | 0.6 in per foot |
| Drainage | Moderately well drained, group D | Well drained, group C |
| Salt | 1.0 dS/m, low | 6.0 dS/m, salty |

**BC.** SoilGrids (250 m global model) gives sand, silt, clay and organic carbon but not drainage class, water held or salt. The same component must hide a row when its value is missing instead of showing a blank.

**Where it goes.** A fifth answer on **Field now**, "What is the soil like?", under the soil moisture answer, plus the existing detail rows kept in More detail. Not on Compare as a score; one sentence in the Compare water panel (below).

**Spec.**
- **Visual:** one horizontal stacked bar, sand (tan) / silt (light) / clay (brown), labelled with the percentages and the texture name above it ("Clay loam"). Reuse the fixed data-colour rule: these are new data colours, so add them to `lib.ts` and never use them for chrome. A soil triangle needs about 240 px of width and adds nothing a grower reads faster; leave it for a later More detail view.
- **Three plain facts** (templates, values from `soil`):
  - "Holds 2.1 in of water per foot." (Kings: "Holds 0.6 in per foot. Low.")
  - "Drains slowly." / "Drains fast." (from drainage class and group)
  - "Salt is low." / "Salty: 6.0 dS/m." (4 dS/m is the existing threshold in `shared.tsx`)
- **What it means for rotation** (one fixed sentence each, chosen by rule, shown under the facts):
  - Clay, group C or D, slow drainage: "Clay holds water and drains slowly, so it suits flooded rice; slow drainage limits how much a rotation can improve infiltration." (matches the engine's existing hydrologic-group note, `engine.py` line 531.)
  - Sandy, low water held: "Sandy soil holds little water, so crops that need steady moisture take more irrigation here, and flooded rice would lose water downward."
  - Salty (EC at or above 4): "Salt hurts some crops more than others; check the crop's salt tolerance with your adviser."
- **Engine:** no scoring change. Today the engine uses only the hydrologic group, as context. Do not add soil to scores without a cited rule. A per-crop salt tolerance table would be new data with sources, so it is out of scope here.
- **Effort S:** one component and three templates; the data is already in the payload. Add a sand/silt/clay row to the Sources sheet (already lists SSURGO).

---

## 4. Chat bot (L)

**Fit.** Creativity (a grounded explainer, not a generic chat) and Validity (it reuses the numeral checker already specified in `docs/planner-spec.md` B6.3: "every numeral in a sentence must equal a value/low/high of a referenced SourcedNumber within display rounding"; no code exists yet). It also serves Impact: growers who will not read a glossary will ask a question.

**Conflict to record.** `PLAN.md` (14 Nov) says "Brief wording: fixed templates only for now; no LLM." Keep that: the printed brief stays templates. The chat is a separate, clearly labelled feature that does not write the brief.

**Name.** Five options:
1. **Tally**: keeps the count. A steady bookkeeper who reads you the numbers and says when something isn't one. Recommended.
2. **Walt**: a retired county adviser; patient, dry, short sentences, always says the unit.
3. **Ines**: the field scout who walks the rows; practical, point-first, never guesses.
4. **Gauge**: a rain gauge; exact and calm, answers in one or two lines.
5. **Furrow**: plain and unhurried; says it straight and hands off to your adviser.

Recommend **Tally** ("Ask Tally"): short, about numbers, unisex, and it sets the right expectation (it explains numbers, it does not decide). Voice: plain, units first, one to three sentences, no emoji, no jokes.

**Placement and pattern.**
- Desktop: an "Ask Tally" button in the top bar, right of Map layers, opens a 400 px chat drawer on the right (the map stays visible; the left panel is not covered).
- Tap-to-explain: replace some "What's this?" links with "Explain" that opens the drawer with the question filled in ("Why is soil 48th percentile?").
- Four suggestion chips per screen (e.g. Field now: "Is 1.9 in of rain low?", "What does 48th percentile mean?", "Why is water need above my limit?", "What is greenness 0.24?").
- Phone: "Ask Tally" in the menu plus a pill above the bottom tabs; opens full-screen.
- Under the input, one line: "AI answers from this field's data. Not advice. Don't type personal details."

**What it answers.** Only the numbers on screen and their meaning: what a number is, how it compares with normal, where it comes from, why two numbers differ (for example IMERG vs stations). Anything else gets: "That's one for your adviser." It never says what to plant or do.

**Grounding.**
1. New route `POST /api/locations/{id}/chat` with `{messages (last 4), screen, date}`. The server builds a fact sheet from the same files the other routes serve (location and soil, `nasa_now`, baseline plus top 2 strategies, outlook, daily summary, validation caveats, glossary). Each fact is `{id, label, value, unit, source}`. The browser sends no numbers.
2. The model sees only the fact sheet and must return `{answer, fact_ids}`.
3. Number checker (about 40 lines, in `backend/api/app/`): pull every numeral from the answer (digits, decimals, percents, ordinals; also number words); each must match a fact value or its range within display rounding, and every `fact_id` must exist. On failure, retry once naming the bad numbers; if it fails again, return a template: "I can't quote that reliably. The screen says: <the fact's own sentence>."
4. Refusals (system prompt plus a post-check for banned phrases): no agronomic prescriptions (what to plant, when, how much water, fertiliser, pesticide), no water-rights, insurance or legal advice, no forecasts beyond the NOAA outlook as shown. Out of scope returns a fixed string without a second call.

**Model and cost.** Anthropic API, **Claude Haiku 5.5** (`claude-haiku-5-5`, $0.10 in / $0.50 out per million tokens up to 100K prompt), `output_config.effort: "low"`, `max_tokens` 400, official `anthropic` Python SDK (add to `backend/api/pyproject.toml`). A question is roughly 4K tokens in and 250 out, so about $0.0005; 2,000 questions cost about $1. (OpenRouter with a similar small model is the fallback if we cannot get an Anthropic key; same route, different client.)

**Limits.**
- Per IP: 3 per minute and 12 per hour, in memory.
- Global: 300 questions a day, plus a cost counter that returns "Tally is resting" past $2 a day. In-memory counters reset when Render restarts, so the real cap is a monthly spend limit (about $10) set on the Anthropic workspace.
- Input 300 characters; history 4 turns.
- `GET /api/chat/status` returns `{enabled}`; with no key the button is hidden and the route returns 503.

**Privacy.** No chat logs, no database. History lives in browser memory only (not `localStorage`). The server does not log message text; it keeps only counters (requests, tokens, checker rejections). Questions do go to Anthropic under its API terms, hence the one-line note.

**Keys.** `ANTHROPIC_API_KEY` in the repo `.env` is empty (line 7; `.env` is git-ignored). `OPENROUTER_API_KEY` is only in `.env.example`, not in `.env`. Needed: an Anthropic key (whoever owns the account), put in `.env` locally and added to Render as a secret. Add `ANTHROPIC_API_KEY` with `sync: false` to `render.yaml`; nothing goes in the Dockerfile or the frontend. Set the workspace spend limit before the key goes live.

**Build order inside item 4:** fact sheet and checker with a canned model response (testable offline, add a check to `backend/api/checks/check_api.py`), then the route with limits, then the drawer, then chips. Test with 20 questions including 5 out-of-scope and 5 prescription traps; zero unchecked numbers.
