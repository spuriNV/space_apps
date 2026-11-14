# CropLytics: working plan

One product, one look, four screens. No more option rounds unless something is clearly broken; we change things by editing the one version. Judged on the rubric in `docs/judging-rubric.md`. Submission is due Sunday 23:59; feature freeze is Saturday 22:00.

## What we're building

A grower and their adviser open one field and get answers to three questions:
1. **What's happening on my field?** This season, in plain words and grower units.
2. **What's likely this coming season?** Outlooks for water, rain, heat and when the field is exposed.
3. **What should I plant next, and what does it cost me in water and risk?** Today's rotation against three alternatives.

They finish by printing one page for the adviser.

## Decisions (made; change only on purpose)

| Topic | Decision |
|---|---|
| Layout | Variant B: satellite map, field panel on the left, timeline along the bottom, 3D stack when you scroll in. |
| Look | **One look:** the "Extension bulletin" style (green header band, slab headings, paper panel), cleaned up. The theme switcher and the other two looks are removed. Rules live in `.claude/skills/fieldshift-visual-design/`. |
| Years shown | **This season plus the last 3** by default (2023–2026). The 2022 drought and 2023 floods appear in the story and pitch, not as a 10-year grid farmers have to read. Older years sit behind "Show earlier years". |
| Your field's year | Simplified: one strip per season (3–4 strips), a "typical year" strip on top, and one sentence on what's different this year. |
| Compare | "Gain / give up vs today": pick an alternative and see two plain lists in acre-feet, days and dollars. The full table is one click away. |
| Brief | One printable page, rewritten for farmers: what the field is, what's likely this season, the option chosen, what it gains and gives up, what to check locally, and sources. |
| Story mode | Pitch only, not in the main app. |
| Archive | Variants A, B and C, `design/explorations/` and the old screenshots stay in the repo for reference but are no longer maintained. |

## The four screens

1. **Pick your field.** Two example fields, named the way a farmer would name them. A "Why not BC yet" note.
2. **Your field now.** More detail than today, in grower units:
   - crop and growth stage;
   - green cover;
   - rain so far this season vs normal (inches);
   - crop water use so far vs normal;
   - estimated irrigation need vs the water limit (acre-feet);
   - soil moisture and groundwater vs normal;
   - heat and frost days;
   - soil type, drainage and salinity;
   - what happened on this field in the last 3 seasons.
3. **Coming season (new).** Outlooks, clearly labelled as outlooks, not forecasts:
   - the winter rain and temperature outlook;
   - reservoir storage now vs average, and what that has meant for water allocations before;
   - the drought outlook;
   - snowpack and runoff forecast once it is published;
   - the expected bare window this winter and the chance of a heavy-rain day landing in it;
   - expected irrigation need for next season per rotation, as a range, shifted by the outlook.
4. **Compare and print.** Gain/give-up comparison, then the one-page brief.

## Data for "this coming season" (no keys needed unless noted)

| Outlook | Source |
|---|---|
| 3-month temperature and rain outlook | NOAA Climate Prediction Center seasonal outlooks |
| Drought outlook and current drought | US Drought Monitor; NOAA seasonal drought outlook |
| Reservoir storage now vs average | CDEC (already cached through 2025; extend to today) |
| Snowpack and runoff forecast | CDEC Bulletin 120 (published from February) |
| Water allocation context | State Water Project and Central Valley Project announcements |
| Expected bare window and heavy-rain chance | This field's satellite calendar plus rain history |
| Soil moisture and groundwater now | SMAP and GRACE (**needs Earthdata login**) |
| Crop water use so far this season | OpenET (**needs key**); NASA POWER and stations as the fallback |

## Backend priorities

1. **Outlooks** for the coming-season screen (table above). Started.
2. **NASA data:** run `backend/nasa` as soon as the Earthdata login is in `.env`; add NASADEM, HLS and ISS photos (started, no login).
3. **Validation:** OpenET vs our model as soon as the key is in; show stations next to POWER for heat and rain.
4. **Scoring fixes:** the team decides the open formula questions in `backend/engine/README.md`.

## Frontend priorities

1. Apply the decisions above to `frontend/app/`: one look, 3–4 seasons, the more detailed "Your field now".
2. Add the coming-season screen from the outlook data.
3. Swap in the simplified Year and the gain/give-up Compare.
4. Rewrite the brief for farmers.

## Pitch (3 minutes)

| Part | Time | Content |
|---|---|---|
| BC opener | 30 s | The 2023 irrigation order and the 2021 Sumas flood; BC lacks the ground data to prove a tool works, so we built and validated it where the data is rich. |
| Demo | 2 min | Colusa field: what happened in 2022 and 2023 (story mode), what's likely this winter, compare, print. |
| Close | 30 s | Supports, never replaces; every number sourced and checked against the ground; next stop, BC. |

Deliverables: 7 slides or a 30-second video, a recorded backup of the demo, and three rehearsals.

## Waiting on people

- **Keys (grokbot):** Earthdata login first, then OpenET (see `SIGNUPS.md`).
- **Team:** decide the scoring-formula fixes.
- **Anyone:** show the app to one real grower or farm adviser for 10 minutes and write down what confused them.

## Decisions made 14 Nov (afternoon)

| Topic | Decision |
|---|---|
| Scoring formulas | Fix them (erosion baseline, pest-break, sorghum-sudan water, rice-then-wheat bare days). Engine owner fixes with cited reasons; checks updated. |
| Machine-learning calendar | Shown as a comparison next to the rule-based calendar, not as the answer. Kings carries "below accuracy target" in plain words. |
| Default water limit | Pre-filled example per field, clearly labelled "example, change to yours": Colusa 5.0 acre-ft/acre, Kings 3.0. |
| Heat threshold | 104 °F (40 °C) everywhere, counted from NOAA stations. |
| Brief wording | Fixed templates only for now; no LLM. |
| ISS photos | Used, captioned "Seen from the ISS near your field, March 2020", with NASA's credit line. |
| Options | No more option rounds. Build one version; change it after review. |
