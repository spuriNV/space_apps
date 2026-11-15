# Next steps (written 2026-11-15, before a usage-limit cap)

Any session can pick this up. Use the `subagent-models` skill: Sonnet for builds, Haiku for checks. Push only through the gate:
- check_api ALL PASS;
- engine checks unchanged;
- `VITE_API_BASE=/api npm run build` green;
- `git pull --rebase` first; never force-push.

## 1. Bring in the `sp` branch (teammate spuriNV), cherry-picking, NOT merging
- `origin/sp` (head 125a153, "removed unnecessary info") branched from old main dc84b98. Merging it would delete about 46k lines of current work (mock data, the redesign, newer features), so don't merge it.
- What it adds is worth porting onto current main:
  - `components/ui/FieldTimeline.tsx`: the "steps" timeline. Integrate it as the field's step-by-step story.
  - `components/compare/SimRun.tsx`: a run/simulate step in Compare.
  - `components/ui/Cedar.tsx`: check what it is (likely a guide or assistant), then integrate it or drop it.
  - `components/ui/FirstNations.tsx`: compare it with main's First Nations card and Nation tools tab, and keep the best of both.
  - Its "removed unnecessary info" trims in App.tsx, ComingSeason, ComparePanel and FieldNow: apply the same trims on main.
  - Backend: `bsr_salmon_forage` (location.json, first_nations.json, polygon). Check whether it duplicates `bc_salmon_river_forage`; if so, keep one id.
- How:
  1. `git diff main...origin/sp -- <file>` per component.
  2. Port each into current main as a new commit on branch `port/sp`.
  3. Gate, then push.
  4. Tell spuriNV what was ported.

## 1b. Port sp's numbered step flow (user priority)
- In sp, `FLOW` in components/ui/shared.tsx and the `tb-tabs` nav in App.tsx: 1 Pick your field → 2 Your field now → 3 Coming season → 4 Compare rotations → 5 Print for your adviser. Each tab has a one-line "does" hint, and the tabs are locked until a field is picked.
- Also sp's `Workflow` component (problem → what this tool does → goal), shown on Pick.
- Implement on main in the redesign style: a pill segmented control in the top bar, numbered, with the tonal selected state. On phone, use the bottom tab bar with the same 5 steps.
- Map main's existing panels into the steps; nothing is lost:
  - Now = This week + Field now + Nation tools (if any);
  - Season = Coming season + salmon (BC);
  - Compare = Compare + sim;
  - Print = brief.
- Preview sp: tailnet https://beelink.tail7cbcab.ts.net:8444 (worktree /home/caiden/nasa/space_apps-sp, static build).

## 2. Cleanup: cut the UI to the key functionality
The user finds it busy: "a lot of things going on… see what is for what and cut it to the key functionality".
- **Keep, front and centre:**
  1. the field panel (This week → Field now → Compare rotations);
  2. tap-anywhere;
  3. draw your field;
  4. Nation tools (top priority for the user);
  5. salmon (BC).
- **Move behind "More detail" or one "Data & sources" tab:** dataset lists, model reports, validation charts, the glossary, and catalog filters.
- **Give every panel a one-line purpose label**, so the user can see what each section is for.

## 3. Bug: BC drawn fields get US-only analysis
- A field drawn at 49.09 N, 122.52 W (Fraser Valley) shows "Outside the US counties" and "This may not be farmland. The USDA crop map shows little or no cropping…".
- Cause: myfields (`backend/api/app/myfields/build.py`) calls the US tier-1 path. BC tier-1 lives in `backend/api/app/anyloc/bc.py` (ECCC, SLC soil, AAFC ACI crop history, ALR parcel).
- Fix: when the polygon centroid is in BC, use the bc.py fetchers. The crop history and "may not be farmland" logic must use AAFC ACI, not CDL. Region-aware wording: say "regional district", not "county". Add a check: a BC rectangle gets region bc and ACI crop history.

## 4. Smaller follow-ups
- Uncommitted half-done speed work in the main checkout (backend/api/app/main.py, frontend/app/vite.config.ts): finish it (GZip middleware, Cache-Control, a maplibre chunk) or `git checkout --` them.
- Mobile: check that the sheet snap points clear the tab bar, and that the draw and Nation tools cards fit at 390 px.
- Wow animation: "Ten years from orbit" prototype in ui-research/wow (plan in WOW.md). Build it after the cleanup.
- Speed: `/api/locations/pt_*/strategies` can take up to 45 s, which holds up the tap-anywhere panel. Make it faster: cache by the 50 km POWER cell, return the default-weights score first, compute the full ranges after.
- Pitch: apply the gaps page (docs/past-winners/REPORT.md). Member names on slide 1, video ≤ 30 s.

## Hosting (done)
- https://croplytics.xyz is a Cloudflare named tunnel to beelink:8787. It auto-deploys from main every 2 min via the croplytics-deploy timer.
- Fallback: croplytics-app.onrender.com.
- Tailnet-only: beelink.tail7cbcab.ts.net:8443.
