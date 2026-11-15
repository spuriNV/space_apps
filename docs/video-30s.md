# CropLytics: 30-second commercial

A 30-second, 16:9 (1920×1080, 24 fps) commercial for CropLytics, our NASA Space Apps 2026 entry (challenge: **Field Shift: Adapting Farms with NASA Data**). Live app: <https://croplytics.xyz>.

Written 15 Nov 2026. It replaces the slide-based plan in `docs/pitch.md` §3 when there is time to shoot it; if not, that plan is the fallback. Every claim comes from `docs/pitch.md` and respects its "Words to avoid" list and `docs/critical-review.md` §5.

**The idea in one line:** a California rice grower stands at a dry field asking "what do I plant next?", opens CropLytics on his phone, drills into that field from space, then works it through on the laptop at the kitchen table. Apple-style: real person, real product, few words, the app doing the talking.

**The mix:** 5 AI-generated live-action shots of one farmer (about 10.5 s), 6 screen recordings of the real app (about 16 s), one end card (3.5 s). One optional stock aerial as a spare.

**Hard limits (Space Apps 2026 submission guide, checked 15 Nov 2026):**
- "The video pitch must be 30 seconds or less." Over the limit means not eligible for global judging. Export exactly 720 frames at 24 fps and check with `ffprobe` before uploading.
- AI-generated "Images and videos: Must include a visible watermark to indicate SI generation. Audio: Must acknowledge SI generation in descriptive text and metadata." (The 2026 rules call AI "SI".) Every AI shot below carries a small visible "AI-generated" mark; see section 8.
- Submission closes **Sunday 15 Nov, 23:59 local time**. If the shoot and edit won't fit before then, submit the slide-based video in `docs/pitch.md` §3 and keep this one for the pitch and social posts.

---

## 0. As built: v1 ($0, 15 Nov 2026)

`video/croplytics-30s-v1.mp4` (+ `.srt`), built by `video/scripts/build.mjs`; sources and licences in `video/CREDITS.md`. It differs from the plan below in four ways: no AI footage (Mixkit stock, all Free-licence, replaces the AI farmer), it opens on the ISS photo, the farmer part is short (about 4.5 s, after `docs/past-winners/REPORT.md`), and it runs **29.5 s (708 frames)**. The voice is a text-to-speech placeholder (edge-tts, `en-US-AndrewNeural`), kept as its own stem so a better read can replace it (`VO_DIR=... node video/scripts/build.mjs`).

| # | Time | Len | Source | Picture | On screen (eyebrow / text / source line) | Voice-over |
|---|---|---|---|---|---|---|
| 1 | 0:00.00–0:02.25 | 2.25 | NASA | ISS photo ISS062-E-81143 (Sacramento Valley, Sutter Buttes), slow push-in | "The Sacramento Valley, seen from the International Space Station"; credit line, NASA JSC | (music) |
| 2 | 0:02.25–0:04.25 | 2.0 | STOCK | Mixkit #521, man in a hat at sunset looking out | | "Every season, the same question." |
| 3 | 0:04.25–0:05.75 | 1.5 | STOCK | Mixkit #42382, hand to the hat, sunset | | "What do I plant next?" |
| 4 | 0:05.75–0:06.75 | 1.0 | STOCK | Mixkit #594, hands with a phone in dry grass (cropped) | | |
| 5 | 0:06.75–0:10.75 | 4.0 | REC phone | iPhone 15 simulator, Safari: pick list, tap the Colusa card, fly in, sheet up to rain 1.9 in and water need 5.2 acre-ft/acre | A real field: one of 10 in California, plus one in British Columbia / Rice field 4 miles east of Williams · 149 acres · Colusa County / NASA HLS (Landsat + ESA Sentinel-2) · NASA GPM IMERG rain | "CropLytics reads your field with NASA Earth data." |
| 6 | 0:10.75–0:11.50 | 0.75 | STOCK | Mixkit #32139, older man at a laptop | | |
| 7 | 0:11.50–0:14.00 | 2.5 | REC laptop | 3D view under the field, slow orbit | Different observations, different scales / Crop · soil moisture · groundwater in the basin / ESA Sentinel-2 · NASA GRACE-FO | "From the crop down to the groundwater." |
| 8 | 0:14.00–0:16.25 | 2.25 | REC laptop | This field's year, earlier years open, 2022 row outlined | Understand risk / 2022: left fallow in the drought / NASA HLS · GPM IMERG | "What happened here." |
| 9 | 0:16.25–0:18.25 | 2.0 | REC laptop | Coming season, "Wetter than normal this winter. An outlook, not a forecast." | Make uncertainty visible / An outlook, not a forecast / NOAA CPC · CDEC | "What's likely this winter." |
| 10 | 0:18.25–0:22.00 | 3.75 | REC laptop | Compare: click Dry-year safflower, zoom to You gain | Compare rotations · reveal trade-offs / Dry-year safflower: about 2 acre-ft/acre, an upper bound. Rice today: about 5. / NASA POWER | "What a switch costs: about two acre-feet, not five." |
| 11 | 0:22.00–0:25.50 | 3.5 | REC laptop | Print for your adviser: the brief drops in and scrolls to "Check locally" | One page for the grower and adviser / Water estimate checked against OpenET: runs 16–21% high, nothing tuned. | "One page for your adviser, checked against OpenET." |
| 12 | 0:25.50–0:29.50 | 4.0 | GFX | End card: CropLytics, "Your field. Your call.", "Plan next season's rotation with NASA Earth data.", "10 real California fields and one in British Columbia. Next: co-design with First Nations farmers.", "NASA Space Apps Challenge 2026 · Field Shift: Adapting Farms with NASA Data", URL, synthetic-voice note | | "CropLytics. Your field. Your call." |

Not on screen, on purpose: SMAP (the 3D view labels soil moisture as "NASA GRACE-FO with a land model", so the video doesn't name SMAP), MODIS, ECOSTRESS, the 14-field registry (the live pick list shows 10 California fields plus BC; set `N_CA` in the build if that changes), and any First Nations co-development claim.

---

## 0b. As built: v2 (15 Nov 2026)

`video/croplytics-30s-v2.mp4` (+ `.srt`), same pipeline (`video/scripts/record-laptop.mjs`, `build.mjs` with `VO_DIR`), **29.5 s (708 frames)**, -14.2 LUFS. Laptop shots re-recorded from croplytics.xyz; N_CA=14 (live `/api/locations`: 14 CA + 1 BC). Phone, stock, ISS, music reused from v1. Voice is synthetic (edge-tts), noted in metadata, CREDITS.md and the end card.

| # | Time | Len | Picture | Voice-over |
|---|---|---|---|---|
| 1 | 0.00 | 1.75 | ISS photo | (music) |
| 2-4 | 1.75 | 4.0 | Stock farmer: looking out, hand to hat, phone in hand | "Every season, the same question." / "What do I plant next?" |
| 5 | 5.75 | 3.5 | Phone recording (v1 clip), Colusa field | "CropLytics reads your field with NASA Earth data." |
| 6 | 9.25 | 0.5 | Stock: man at a laptop | |
| 7 | 9.75 | 2.5 | "This week" card (irrigation, field access) | "This week, in your field." |
| 8 | 12.25 | 2.5 | 3D view under the field | "From the crop down to the groundwater." |
| 9 | 14.75 | 2.5 | Nation tools: drought rotation bars | "If the water stops, what holds?" |
| 10 | 17.25 | 4.0 | Compare: dry-year safflower | "What a switch costs: about two acre-feet, not five." |
| 11 | 21.25 | 3.0 | One-page brief, OpenET line ("runs 16-21% high, nothing tuned") | "One page, checked against OpenET." |
| 12 | 24.25 | 2.0 | Overview with clustered farm pins, then Draw a field: 27 acres | |
| 13 | 26.25 | 3.25 | End card, croplytics.xyz | "CropLytics. Your field. Your call." |

Dropped from v1: "This field's year" and "Coming season". Weak spots: the phone clip is the v1 app UI; the draw shot stops at the acres because saving a drawn field on the live app crashed the page ("Cannot read properties of undefined (reading 'years')"); lower-third boxes sit over the left panel as in v1.

---

## 1. Shot list (sums to 30.0 s)

Sources: **AI** = generated video (section 7 prompts), **REC** = screen recording of the real app (section 4), **GFX** = motion graphics built in the edit, **STOCK** = free stock fallback.

| # | Time | Len | Source | Visual | Camera | On-screen text | Voice-over | Music |
|---|---|---|---|---|---|---|---|---|
| 1 | 0:00.0–0:03.0 | 3.0 | AI | Golden hour, Sacramento Valley. A dusty green utility tractor idles at the edge of a dry, bare rice field (cracked mud between low levees, old stubble). The farmer climbs down the step and drops to the gravel. Sutter Buttes faint on the horizon. | Wide, locked off at knee height, slight telephoto (50–85 mm look). He steps into frame. | "AI-generated" mark, bottom right | (none: engine idle, boots on gravel) | Room tone, then one soft piano or muted guitar note at 0:01.5 |
| 2 | 0:03.0–0:05.5 | 2.5 | AI | He stands at the levee and looks out over the bare field, grass stalk in the corner of his mouth, squinting into low sun. | Medium close-up, slow push-in (dolly), shallow depth of field, field soft behind him. | "AI-generated" mark, bottom right | "Every season, the same question." | Simple pulse starts (light kick or hand percussion, about 100 BPM) |
| 3 | 0:05.5–0:07.5 | 2.0 | AI | He tips his cap back and scratches his head, chewing the grass stalk once. | Medium shot, locked off, profile three-quarter. | "AI-generated" mark, bottom right | "What do I plant next?" | Hold |
| 4 | 0:07.5–0:09.0 | 1.5 | AI | His hand pulls a phone from the bib pocket of his overalls; thumb taps. Screen faces away or is soft and blown out (no fake UI). | Insert close-up on hands and bib pocket, handheld, slight rack focus. | "AI-generated" mark, bottom right | "CropLytics reads your field..." | Rising pad, first beat lands on the cut to 5 |
| 5 | 0:09.0–0:13.0 | 4.0 | REC (phone) | The real app on an iPhone: map of California with the field pins, tap the Colusa rice pin, the satellite map flies in to the field's yellow corner ticks, the "Your field now" sheet slides up (2026 strip, rain 1.9 in, water need 5.2 acre-ft/acre). | Clean phone frame floating on a soft paper-coloured backdrop (`#f7f6f0`), slow 3% scale-up; or full-bleed screen. | Lower third, after the sheet is up: **Rice field 4 miles east of Williams · 149 acres · Colusa County** | "...with NASA Earth data." | Beat drops in on the tap |
| 6 | 0:13.0–0:14.5 | 1.5 | AI | Evening, farmhouse kitchen. Same farmer (cap off, on the table), sits at a wooden table and opens a laptop. Warm lamp, blue dusk in the window. Screen glow on his face; screen not visible. | Medium, from across the table at eye level, slow push-in. | "AI-generated" mark, bottom right | (none) | Pulse continues |
| 7 | 0:14.5–0:17.0 | 2.5 | REC (laptop) | The 3D view under the field: crop block, root-zone soil moisture layer, basin groundwater layer, with their labels. Slow orbit. | Full-bleed browser content (no browser chrome), slight zoom. | Small, bottom left: **Crop · soil moisture · groundwater in the basin** | "From the crop down to the groundwater." | Hold |
| 8 | 0:17.0–0:19.5 | 2.5 | REC (laptop) | "This field's year", earlier years open, the 2022 strip all brown. | Full-bleed, slow pan down to the 2022 row; 2022 row highlighted with a thin yellow `#ffd166` box. | **2022: left fallow in the drought** | "What happened here." | Hold |
| 9 | 0:19.5–0:21.5 | 2.0 | REC (laptop) | "Coming season": the three answers, header "Wetter than normal this winter. An outlook, not a forecast." | Full-bleed, slight zoom on the header. | **An outlook, not a forecast** (the app's own words, already on screen) | "What's likely this winter." | Small lift |
| 10 | 0:21.5–0:25.0 | 3.5 | REC (laptop) | "Compare": click the "Dry-year safflower" card; "You gain" and "You give up" lists appear. | Full-bleed, zoom from whole panel to the "You gain" column. | **Dry-year safflower: about 2 acre-ft/acre, an upper bound. Rice today: about 5.** | "What a switch costs: about two acre-feet, not five." | Build |
| 11 | 0:25.0–0:26.5 | 1.5 | REC (laptop) | "Print for your adviser": the one-page brief slides in and scrolls once to "Check locally before anything is seeded". | Full-bleed; the page drops in as a sheet of paper. | small: **Water model checked against OpenET: runs 16–21% high** | "And one page for your adviser." | Music resolves |
| 12 | 0:26.5–0:30.0 | 3.5 | GFX | End card (section 3). | Static, 0.4 s fade from 11. | End card | "CropLytics. Your field. Your call." | Last note rings out, ends at 29.6 |

**Total: 3.0 + 2.5 + 2.0 + 1.5 + 4.0 + 1.5 + 2.5 + 2.5 + 2.0 + 3.5 + 1.5 + 3.5 = 30.0 s.**

Spare (not in the cut): **STOCK or AI**, a sunrise drone shot over flooded or bare Sacramento Valley rice checks. Use it in place of shot 1 if the tractor shot fails, or under the end card at 30% opacity.

**Shot 5 trick (no fake phone screens):** the AI shots never show a readable screen. The real app appears only in clean screen recordings, in a phone frame or full-bleed, the way Apple ads cut from the person to the product. If a take of shot 4 or 6 happens to have a flat, steady screen, a corner-pin of the matching recording can go in (DaVinci Resolve's planar tracker, free), but don't plan on it.

---

## 2. Voice-over script

Read calm and warm, unhurried, a mid-range American voice, close to the mic. Not an announcer.

> Every season, the same question.
> What do I plant next?
> CropLytics reads your field with NASA Earth data.
> From the crop down to the groundwater.
> What happened here.
> What's likely this winter.
> What a switch costs: about two acre-feet, not five.
> And one page for your adviser.
> CropLytics. Your field. Your call.

**52 words**, about 21 s of speech inside 30 s, which leaves room for the opening and the cuts to breathe. Apple spots run well under the 70–80 word ceiling; don't fill the gaps.

Why each line is safe (`docs/pitch.md`, "Words to avoid"):
- "NASA Earth data": the screens show NASA HLS, GRACE-FO, GPM IMERG, NASA POWER, NASADEM and ISS photos. No dataset list in the VO, so nothing can be out of date on the day.
- "Down to the groundwater": the on-screen label says "in the basin", matching the app's "Basin-wide signal, not your own well".
- "About two acre-feet, not five": the pitch's own rounding; "upper bound" is on screen in shot 10. Never "saves 3.4 acre-feet".
- "What's likely this winter": an outlook; shot 9 shows "An outlook, not a forecast". Never "forecast" or "real-time".
- "Your call": the ad's version of "supports the grower and adviser; it doesn't replace them".
- Not used: "validated", "accurate", "AI", any percentage accuracy, "works for any farm", the 2023 floods at this field, a field count.

**Captions:** burn them in (most people watch muted) and also ship a sidecar `.srt`. Captions in Libre Franklin 600, 40 px at 1080p, ink on a paper box, bottom centre, never over a screen recording's own text (move them up in shots 8–11 if they collide).

---

## 3. End card (0:26.5–0:30.0)

Paper background `#f7f6f0`, a 6 px spot-green band (`#2f5d34`) across the bottom edge.

- **CropLytics** wordmark: Zilla Slab 600, 140 px, spot green, centred, slightly above middle. Same as the app's top-left wordmark; no icon tile, no gradient.
- The line, under it: **Plan next season's rotation with NASA Earth data.** Libre Franklin 400, 40 px, ink `#191c16`.
- Bottom, small: **NASA Space Apps Challenge 2026 · Field Shift: Adapting Farms with NASA Data**, then **Team &lt;team name&gt; · croplytics.xyz**, Libre Franklin 400, 26 px, muted `#5a5e54`. (The submission guide's suggested video opens with your name and team; this spot puts the team on the end card instead.)
- Bottom right, 20 px muted: **Farmer scenes, voice and music are AI-generated.** This is the disclosure the rules ask for, in addition to the per-shot watermark.
- Animation: wordmark fades up 12 px over 0.5 s, the line follows 0.3 s later, small text last. Hold still for the final 2 s.
- **No NASA "meatball" insignia or worm logo.** Text only (see section 8).

---

## 4. What to screen-record, and how

Record once the data is final, on the same day as the edit, so the numbers match the pitch. Field: **car_colusa_rice** (shown as "Rice field 4 miles east of Williams" in today's screenshots; use whatever name the app shows on the day and match the lower third to it). Check before recording that SMAP, MODIS or ECOSTRESS labels on screen still match what `docs/pitch.md` allows.

Before any take: wake the Render server (open the live URL and wait for data, up to a minute), or run the API locally (`cd backend/api && uv run uvicorn app.main:app --port 8000`) and the app on `localhost`. Do not record the "Example numbers" or "Waking the server" states.

### Shot 5: phone (web app's phone layout in the iOS Simulator)

The native iOS app (`apps/ios`) opens a field from a list; only the web app does the fly-in from California to the field, which is the "drill down" the story needs. So record the web app on a simulated iPhone:

1. `open -a Simulator`, boot an **iPhone 15 Pro** (iOS 17.5 is installed), Appearance light.
2. In Safari open <https://croplytics-app.onrender.com>, Share > **Add to Home Screen**, then launch from the home screen icon so Safari's address bar is gone (if it still shows, crop it in the edit; the phone frame hides it).
3. Status bar: `xcrun simctl status_bar booted override --time 9:41 --batteryLevel 100 --batteryState charged --cellularBars 4 --wifiBars 3`.
4. Start recording: `xcrun simctl io booted recordVideo --codec h264 --force shot05_phone.mp4`. Ctrl+C to stop.
5. Take: wait 1 s on the California overview with pins, tap the Colusa rice pin (or its card in the pick list), let the map fly in, wait for the yellow corner ticks, drag the sheet to half so "Your field now" shows the 2026 strip, rain and water need. Hold 2 s. Do 3 takes.
6. Native alternative (if the web phone layout misbehaves): `xcrun simctl launch booted <bundle id> -initialField car_colusa_rice -initialTab fields`, tap the field, scroll "Field now". Less of a fly-in, but it is the real native app. Android: `adb shell screenrecord --size 1080x2400 /sdcard/shot05.mp4` on an emulator (no AVD is set up on this Mac yet; create one in Android Studio's Device Manager, Pixel 8, API 34).

### Shots 7–11: laptop (web app in Chrome)

The app's layout is tuned at 1440×900; a 16:9 recording needs **1600×900 CSS pixels** (Compare keeps three columns above 1280 px, Coming season keeps its three cells above 1180 px).

1. Open Chrome at exactly that size: `open -na "Google Chrome" --args --new-window --window-size=1600,990 --app=https://croplytics-app.onrender.com` (app mode drops the tab strip and address bar; the extra 90 px is the title bar). Zoom 100%, Do Not Disturb on, hide the Dock, desktop clean.
2. Record with macOS: Cmd+Shift+5 > **Record Selected Portion**, drag exactly over the page area, Options > no microphone, **Show Mouse Clicks off**. On a Retina screen that gives 3200×1800, which scales down cleanly to 1920×1080. (Command line alternative: `ffmpeg -f avfoundation -capture_cursor 0 -framerate 60 -i "1:none" -vf crop=...`.)
3. Move the pointer slowly and deliberately, or hide it: Apple-style spots show taps, not cursors. Record each shot as its own take, 2–3 takes each, starting 1 s before and ending 1 s after the action:

| Shot | Start state | Action to record |
|---|---|---|
| 7 | Colusa field open, "Field now" | Click **3D** (map control, right). Let it settle on crop, soil moisture and groundwater layers with their labels; slowly drag to orbit about 20°. |
| 8 | "This field's year" tab | Click **More detail** / "Show earlier years", let the strips render, rest on the 2022 row (brown nearly all year). |
| 9 | "Coming season" tab | Open it, hold on the green header "Wetter than normal this winter. An outlook, not a forecast." and the three answers. |
| 10 | "Compare" tab | Click the **Dry-year safflower** card; hold on "You gain" (less irrigation water) and "You give up" (field bare more days). |
| 11 | "Print" tab | Open "Print for your adviser"; scroll once to "Check locally before anything is seeded". |

A Playwright script (like `design/tools/shoot-app.mjs`, `headless: false`, `slowMo: 250`) can drive the same clicks for repeatable takes while macOS records the window. Playwright's own `recordVideo` is low bitrate VP8; don't use it for the final.

---

## 5. Style guide

**Tone.** Apple's "Shot on iPhone" and Mac product spots: one person, a real problem, the product shown working, no hype words, quiet confidence, the last line short. Respectful of the grower: he knows his ground; the app answers his question in his units. The overalls and the grass stalk are the costume, not the joke; he is competent and thoughtful, never a punchline.

**Colour grade.**
- Exteriors (1–4): natural golden hour, warm highlights, slightly lifted shadows, low saturation in the greens (it's a dry field), soft film grain. Avoid teal-and-orange.
- Interior (6): warm tungsten lamp vs blue dusk window; skin tones natural.
- Screen recordings: no grade. The app's paper `#f7f6f0`, ink `#191c16` and spot green `#2f5d34` must stay exact so the product looks like the product.
- Match the grade of the AI shots to each other with one LUT or one Resolve node applied to all five.

**Type** (from `.claude/skills/fieldshift-visual-design`, matching the app):
- Headings, the wordmark and the big supers: **Zilla Slab** 500/600.
- Lower thirds, captions and small text: **Libre Franklin** 400/600, `tabular-nums lining-nums` for numbers.
- Sentence case everywhere, no all-caps eyebrows, no monospace, no em dashes, no gradient text, no glow.
- Text never sits straight on footage: lower thirds sit in a solid paper box (`#f7f6f0`, 1 px ink border, 2 px shadow), like the app's map labels.
- Units the grower uses: acres, inches, acre-feet per acre. No mm, no hectares.

**Pacing.** Slower human shots (2–3 s), quicker product shots (1.5–2.5 s), one 4 s hold on the drill-down because it is the moment. Cut on action (step down, head scratch, tap). Every cut lands on a beat. The last 3.5 s are still.

**Music.** Sparse, warm, acoustic: muted piano or fingerpicked guitar plus a soft pulse, 95–105 BPM, building gently to the compare shot and resolving on the brief. No vocals. Mix VO at -14 LUFS integrated for the whole spot (YouTube), music ducked 8–10 dB under VO.

**Edit and finish.** The DubHacks "Apple-style" video project files are not on this Mac (only `~/job-archive/downloads/dubhacks-handover.md` and `dubhacks-research-brief.md`, which cover the Scrub robot project and its ElevenLabs + Gemini voice path, not the video). Caiden's earlier videos (`~/Documents/dci-paper-video`, `~/Documents/cmpt307-videos`) were built from code: Manim for animation, edge-tts for narration, ffmpeg to mux, with silence pads to keep audio and picture locked. Keep that spirit, but for live action plus product shots use:
- **Remotion** (React, code-driven like the Manim pipeline; Remotion's own Claude Code plugin exists) or **DaVinci Resolve** (free) to cut, place the phone frame, supers and end card. Remotion's licence is free for individuals and small teams; check its terms if the team is larger than 3.
- **ffmpeg** for the final encode: H.264 High, 1920×1080, 24 fps, 12–16 Mbps, AAC 192 kbps, plus burned captions (`subtitles=` filter) and a sidecar `.srt`.

---

## 6. Character bible (keep the farmer the same in every shot)

Paste this block, unchanged, into every image and video prompt:

> **Walt**, a California rice farmer in his late 50s, sun-weathered tanned skin, short salt-and-pepper beard, crow's feet, light blue eyes. Faded blue denim bib overalls over a sun-faded red-and-grey plaid long-sleeve work shirt, sleeves rolled to the forearm. Worn tan mesh-back trucker cap with no logo. Scuffed brown leather work boots. A pale dry grass stalk in the left corner of his mouth. Medium build, slight paunch, calm and thoughtful.

Rules:
1. **Make one reference image first** (section 7, step A), pick the best, and use it as the reference or first frame for every video shot. Don't rely on text alone; text-only generations drift (beard length, shirt pattern, cap colour).
2. Keep wardrobe identical in every shot, including shot 6 (cap off, on the table; same shirt and overalls).
3. Same tractor in shot 1 every take: a dusty mid-size green utility tractor with no visible brand name or logo.
4. Same light per scene: exteriors at golden hour with the sun low behind camera-left; interior at dusk with a warm lamp camera-right.
5. Hands: keep them doing one simple thing per shot (gripping a rail, scratching, holding a phone), keep them small in frame or in motion, and reject any take with wrong finger counts or melting objects.
6. No readable text anywhere in AI shots (no brand names, no phone or laptop UI). The real app only appears in screen recordings.

---

## 7. AI-video prompts

### 7.1 Which AI tool, and do we need a membership?

Checked 15 Nov 2026 on each vendor's own pages unless marked "3rd-party" or "unverified". Cost column = about 90 s generated (6 shots × 5 s × 3 takes) at 1080p. Quality = Artificial Analysis video arena (<https://artificialanalysis.ai/video/leaderboard/text-to-video>, `.../image-to-video`).

| Model, access | Realistic people | Clip length | Character consistency | MCP from Claude Code | Price | ~90 s |
|---|---|---|---|---|---|---|
| **Gemini Omni Flash 1.2** (Google's current video model; Gemini API, Vertex, fal) | #5 text-to-video, #14 image-to-video | 3–15 s, whole seconds | Up to 6 reference images (fal: up to 10); one image can be the literal first frame | **fal official hosted MCP** (OAuth). Google's own genmedia MCP needs Vertex | fal $0.1229/s at 1080p ($0.0819 at 720p); Google direct ≈ $0.104/s (from token rates) | **≈ $11** |
| Veo 3.1 GA (Vertex, fal) | Good, no longer top 15 | 4, 6 or 8 s | Image-to-video, reference images, first/last frame | Google `mcp-veo-go` (Vertex, Cloud Storage bucket, "not an officially supported Google product") | $0.40/s with audio, $0.20/s without; Fast $0.10–0.12/s | $9–36 |
| Seedance 2.5 (fal) | **Best**: #1 image-to-video, #4 text-to-video | 4–30 s | Up to 30 reference images | fal | ≈ $1.16/s at 1080p, $0.47/s at 720p | $105 (720p $43) |
| Kling 4 (fal) | Probably high, not yet ranked | 3–30 s, multi-shot | Up to 7 "elements" (characters), 10 references | fal | $0.157/s (3rd-party says $0.235 at 1080p) | $14–21 |
| MiniMax H3 / Hailuo | #3 text-to-video, #4 image-to-video | unverified | Image-to-video | Official `MiniMax-AI/MiniMax-MCP`, but its README only documents Hailuo-02 | ≈ $0.08–0.13/s (3rd-party); no 1080p tier | $7–12 |
| Runway Gen-4.5 | Good | not checked | Image-to-video | Official hosted MCP, but it needs a **Runway subscription plan** | API $0.12/s | $11 + plan |
| Luma Ray3.2 | Good | 5 or 10 s | Image-to-video | No official MCP (community only) | $1.20 per 5 s at 1080p | $22 |
| Pika | H3 Flex #10 image-to-video | – | Image-to-video | Only through fal | unverified | – |
| OpenAI Sora 2 | – | – | – | – | **Shut down 24 Sep 2026**; no replacement API | n/a |

Aggregators: **fal.ai** has an official hosted MCP (`https://mcp.fal.ai/mcp-relay`, OAuth; tools `search_models`, `get_pricing`, `run_model`, `submit_job`, `upload_file` up to 90 MB) and bills prepaid credits per successful output. **Replicate** has an official hosted MCP (`https://mcp.replicate.com/sse`; its video catalogue and prices weren't checked). Higgsfield's MCP is only described by a 3rd party (unverified).

Voice and music: **ElevenLabs**. The old local MCP (`elevenlabs/elevenlabs-mcp`) is deprecated in favour of a hosted one at `https://api.elevenlabs.io/v1/mcp` (OAuth). Free plan: no commercial licence. **Starter, $6/month ($1 the first month), is the cheapest plan with "Commercial License" and "Music commercial use".** Our VO (about 300 characters) and 30 s of music cost cents inside Starter's credits. Whether the hosted MCP can generate music is unconfirmed; if not, use the ElevenLabs website for the music.

Stock: **Pexels** (free, commercial use, no attribution needed, free API with a key; people "may not appear in a bad light", no implied endorsement) and **Pixabay** (free; restricts commercial use of recognisable people and trademarks). Pexels MCP is community-made (`pexels-mcp-server` on PyPI), not official. Paid libraries (Storyblocks about $21–40/month, Artgrid about $30–50/month, 3rd-party prices) aren't needed for one spare aerial.

### 7.2 Recommended stack

| Job | Tool | Why | Cost |
|---|---|---|---|
| Farmer video (5 shots, 3 takes each) | **Gemini Omni Flash 1.2 on fal**, reference-to-video (`google/gemini-omni-flash/v1.2/reference-to-video`) | Top-5 realism, real character references, one official OAuth MCP, a third the price of Veo 3.1 with audio | 5 × 5 s × 3 = 75 s × $0.1229 ≈ **$9.20** |
| Fallback model, same MCP | Kling 4 on fal (`fal-ai/kling-video/v4/reference-to-video`); Seedance 2.5 at 720p only for a shot that keeps failing (usually the head scratch) | No new signup | ≈ $2–7 per problem shot |
| Character reference sheet and keyframes | Nano Banana 2.1 on fal (edit endpoint `google/nano-banana-2.1/edit`; text-to-image id via `search_models`) | Same MCP; keeps the face, cap and shirt fixed | ≈ **$1–2** for 8–12 images |
| Voice-over and music | **ElevenLabs Starter** (hosted MCP or the website) | Commercial licence for voice and music | **$1** this month, then cancel (else $6/month) |
| Spare aerial | **Pexels** (free) | Landscape only, no people | $0 |
| Edit | Remotion or DaVinci Resolve (free), ffmpeg | Matches the code-driven pipeline used before | $0 |

**Total: about $12–15, worst case about $20.** fal is prepaid pay-as-you-go credits (buy $15–20), not a membership. **The only subscription is ElevenLabs Starter**, and only for its commercial licence. Free fallback for the voice: `edge-tts`, already used in `~/Documents/dci-paper-video` (Microsoft voices; its terms for commercial use are unclear, fine for a hackathon entry, not for an ad that is sold).

### 7.3 Signups and keys (names only; never paste values into chat or commits)

1. **fal.ai:** sign in at <https://fal.ai>, Billing, buy $15–20 of credits. The MCP uses OAuth, so no key is needed for it. Only if you also script fal outside Claude Code, create a key and add **`FAL_KEY`** to `/Users/caide/Documents/nasa-hacks/.env` (name from fal's SDK docs; not re-checked today).
2. **ElevenLabs:** sign up at <https://elevenlabs.io>, subscribe to **Starter**. Hosted MCP uses OAuth. For the local MCP or scripts, add **`ELEVENLABS_API_KEY`** to `.env`.
3. **Pexels (optional):** free key at <https://www.pexels.com/api/>; add **`PEXELS_API_KEY`** to `.env`.
4. Optional: **`GEMINI_API_KEY`** (AI Studio, billing on; no free tier for Omni) only if calling Google directly. There is no official MCP for that route; Google's genmedia MCPs need a Vertex project (`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GENMEDIA_BUCKET`, `gcloud auth application-default login`).

`.env` is already git-ignored. It currently holds the Earthdata, OpenET, CIMIS, NASS, AMS, Anthropic and Render keys; none of them cover video.

### 7.4 MCP setup for Claude Code (not installed yet)

```bash
# fal (official, hosted, OAuth): video and image models
claude mcp add --transport http --scope user fal https://mcp.fal.ai/mcp-relay
# then inside Claude Code: /mcp -> fal -> Authenticate (browser)

# ElevenLabs (official hosted MCP, OAuth). ElevenLabs documents it as a claude.ai connector;
# this Claude Code command uses the standard syntax and is not from their docs.
claude mcp add --transport http --scope user elevenlabs https://api.elevenlabs.io/v1/mcp
# fallback, the deprecated local server, reading the key from .env without typing it:
#   set -a; source /Users/caide/Documents/nasa-hacks/.env; set +a
#   claude mcp add elevenlabs -e ELEVENLABS_API_KEY="$ELEVENLABS_API_KEY" -- uvx elevenlabs-mcp

# Pexels (community server, optional)
#   claude mcp add pexels -e PEXELS_API_KEY="$PEXELS_API_KEY" -- uvx pexels-mcp-server
```

`claude mcp add -e` stores the value in `~/.claude.json` in plain text; prefer the OAuth servers. Run `/mcp` afterwards to check each shows "connected".

### 7.5 Workflow

1. **A. Character sheet** (Nano Banana): one 16:9 image of Walt (section 6) in four views on a plain grey backdrop: front, three-quarter, profile, full body. Generate 4, pick 1. Then make one keyframe per shot (Walt placed in that shot's set and light) with the edit endpoint, using the sheet as the reference.
2. **B. Video** (Omni Flash 1.2 reference-to-video, 16:9, 1080p, 5 s, audio on): pass the sheet as `<IMAGE_REF_0>` and the shot's keyframe as `<IMAGE_REF_1>`, and say in words that `<IMAGE_REF_1>` is the opening frame. 3 takes per shot. Generate 5 s even for 1.5 s shots: the model needs room to settle, and you cut the best 1.5–3 s.
3. **C. Watermark:** add a small "AI-generated" mark to every AI shot in the edit (section 8).
4. **D. Audio:** strip the model's own audio except the ambient tracks you like (tractor idle, birds, boots); VO and music from ElevenLabs.

Prompt rules for Omni (Google's guide, <https://aistudio.google.com/docs/omni#prompt-guide>): say "Continuous, unbroken shot. No scene cuts." (it makes multi-shot clips by default); describe scene, camera, lighting and mood; time actions in words or `[0-2s]` codes; write negatives inline ("No dialogue. No text. No logos."); describe the sound; on fal, refer to references as `<IMAGE_REF_0>`, `<IMAGE_REF_1>` in list order.

### 7.6 Prompts

**A. Character sheet (Nano Banana, 16:9, 2K)**

> Photorealistic character reference sheet on a plain mid-grey studio backdrop, soft even daylight, four views of the same man side by side: front, three-quarter left, left profile, full body standing. [CHARACTER BLOCK from section 6.] Natural skin texture with pores and sun damage, no makeup look, realistic fabric wear on the denim. 50 mm lens, f/5.6, sharp focus. No text, no labels, no logos anywhere.

**Shot 1: off the tractor (5 s, keep 3.0 s)**

> Continuous, unbroken shot. No scene cuts. Use `<IMAGE_REF_0>` for the man's face, beard, cap, shirt and overalls; `<IMAGE_REF_1>` is the opening frame.
> Golden hour in California's Sacramento Valley. A dusty mid-size green utility tractor with no visible brand or logo idles on a gravel farm road beside a dry, bare rice field: flat cracked grey mud between low earthen levees, short pale stubble, a small jagged mountain range faint on the far horizon. [CHARACTER BLOCK.] [0-2s] he swings one leg down from the tractor step, holding the grab handle with his left hand, and steps down onto the gravel. [2-5s] he lands, straightens up and takes two slow steps toward the field, the grass stalk in his mouth.
> Camera: locked-off wide shot at knee height, 85 mm telephoto look, shallow depth of field, warm low sun from camera left, long shadows, gentle film grain, natural colour, cinematic and calm.
> Sound design: diesel tractor idling, boots on gravel, distant meadowlark. No dialogue. No music. No text, no logos.

**Shot 2: looking out (5 s, keep 2.5 s)**

> Continuous, unbroken shot. No scene cuts. Same man as `<IMAGE_REF_0>`; `<IMAGE_REF_1>` is the opening frame.
> He stands on a low earthen levee at the edge of a dry, bare rice field at golden hour and looks out across it, squinting into the low sun, the pale grass stalk in the left corner of his mouth moving slightly as he chews it once. His expression is quiet and thoughtful, a little worried. Light breeze moves his shirt collar.
> Camera: medium close-up from slightly below eye level, slow dolly push-in, 85 mm look, f/2, the field soft and golden behind him, warm rim light, natural skin tones, subtle film grain.
> Sound design: soft wind, a distant meadowlark. No dialogue. No music. No text, no logos.

**Shot 3: the head scratch (5 s, keep 2.0 s)**

> Continuous, unbroken shot. No scene cuts. Same man as `<IMAGE_REF_0>`; `<IMAGE_REF_1>` is the opening frame.
> Standing at the field's edge at golden hour, he slowly lifts his right hand, tips his cap back with two fingers, and scratches the side of his head, then lets the hand drop. He shifts the grass stalk to the other corner of his mouth. Unhurried, natural, a man thinking about what to plant next. One hand, five fingers, simple motion.
> Camera: locked-off medium shot, three-quarter profile, 50 mm look, background of dry field and levees softly out of focus, warm low sun, natural colour, film grain.
> Sound design: wind, faint insects. No dialogue. No music. No text, no logos.

**Shot 4: phone out (5 s, keep 1.5 s)**

> Continuous, unbroken shot. No scene cuts. Same denim overalls and plaid shirt as `<IMAGE_REF_0>`.
> Close-up insert: his weathered right hand reaches into the chest bib pocket of faded denim overalls, pulls out a plain black smartphone in a rugged case, and his thumb taps the screen once. The screen faces away from camera; only a soft glow is visible. No readable screen content.
> Camera: handheld close-up at chest height, 100 mm macro look, slight rack focus from the pocket to the phone, warm golden-hour backlight, shallow depth of field.
> Sound design: denim rustle, a soft tap. No dialogue. No music. No text, no logos, no brand marks on the phone.

**Shot 6: kitchen table (5 s, keep 1.5 s)**

> Continuous, unbroken shot. No scene cuts. Same man as `<IMAGE_REF_0>`, same plaid shirt and overalls, cap off and resting on the table, hair short and greying; `<IMAGE_REF_1>` is the opening frame.
> Evening in a simple farmhouse kitchen: worn wooden table, a ceramic coffee mug, a stack of paper, a warm table lamp on the right, blue dusk through the window behind him. He sits down and opens a plain silver laptop with no logo; the screen faces him, away from camera, and its cool glow lights his face. He leans in, interested.
> Camera: eye level from across the table, slow push-in, 50 mm look, f/2.8, warm tungsten against blue window light, natural skin tones, film grain.
> Sound design: chair creak, laptop opening, quiet room tone, a clock ticking. No dialogue. No music. No text, no logos.

**Spare: aerial (Pexels first; AI only if nothing fits)**

> Continuous, unbroken shot. Sunrise drone shot flying slowly forward over California rice country: a grid of flat rectangular fields separated by thin earthen levees, some flooded and reflecting the pink sky, some bare brown, a straight farm road, low mist. No people, no vehicles with logos, no text. Camera: 120 m altitude, gentle forward glide, slight downward tilt. Sound design: soft wind. No dialogue. No music.

---

## 8. Risks and rules

| Risk | What could go wrong | What we do |
|---|---|---|
| **Space Apps AI rule** | The 2026 submission guide: "Images and videos: Must include a visible watermark to indicate SI generation. Audio: Must acknowledge SI generation in descriptive text and metadata." Also: "SI should not be used to (come up with your idea of how to solve the challenge)." (<https://www.spaceappschallenge.org/resources/project-submission-guide/>) | Every AI shot (1, 2, 3, 4, 6, and the spare if generated) gets a small but legible mark, bottom right: "AI-generated", Libre Franklin 600, 22 px, ink on a 70% paper box. The end card says "Farmer scenes, voice and music are AI-generated." The project text says which tools made what (fal / Gemini Omni Flash, Nano Banana, ElevenLabs), and the file carries it in metadata: `ffmpeg ... -metadata comment="Farmer scenes: Gemini Omni Flash 1.2 via fal. Voice and music: ElevenLabs. App footage: screen recordings of CropLytics."`. The app and its idea are the team's own; AI only makes the ad's footage and voice. |
| **NASA branding** | The same guide: generated content "may not use, contain, or modify any NASA branding or design elements (such as the NASA logos, flags, or mission identifiers)". NASA's insignia ("meatball"), logotype ("worm") and seal may not be used without permission (14 CFR 1221, <https://www.nasa.gov/nasa-brand-center/brand-guidelines/>). The Space Apps brand guide: "DON'T use NASA official branding". | No NASA logos anywhere: not on the end card, not on the farmer's cap, not in prompts. "NASA Space Apps Challenge 2026" and "NASA Earth data" appear as plain text only. The Space Apps logo may be used unaltered under its brand guide, but text is enough. |
| **Minors and real people** | Demos "may not include any images, video, audio, or other likeness to persons under 18"; anyone featured needs written consent (<https://www.spaceappschallenge.org/legal/>). | One clearly adult, fictional farmer. No children in the kitchen or anywhere else. Don't prompt with a real person's name or photo (Omni also blocks recognisable people). Stock footage: landscapes only, no identifiable people. |
| **Uncanny people and hands** | AI faces drift between shots; fingers merge or multiply; the grass stalk teleports; phones and laptops sprout garbage UI. | Character sheet plus keyframes as references; one simple hand action per shot; generate 3 takes and keep the best 1.5–3 s; never show a readable screen; reject any take with wrong fingers, melting objects or text. If the head-scratch fails after 3 takes, try Kling 4 or Seedance 2.5 for that one shot, or reframe it from behind. |
| **Licences** | Free ElevenLabs has no commercial licence. fal's "Commercial use" badge for the Omni 1.2 endpoint wasn't checked. Pixabay restricts recognisable people; Pexels asks for no implied endorsement. Google's terms: "Google won't claim ownership over that content". | ElevenLabs Starter for VO and music. Check the badge and terms on fal's model page before the first paid run. Credit stock in the YouTube description ("Aerial: Pexels / <creator>"). |
| **Map imagery in recordings** | The app's satellite basemap is Esri World Imagery (see `apps/android/README.md`, "Esri's attribution"). | Leave the map's attribution visible where it falls in frame, and credit "Basemap imagery: Esri, Maxar and contributors" in the video description. |
| **Claims drift** | The live numbers change (rain, outlook, water need) and field names have changed before ("3.5 miles" became "4 miles east of Williams"). | Record on the edit day, match supers to what the screen shows, and re-read `docs/pitch.md` "Words to avoid". Never "validated", "forecast", "real-time", "saves 3.4 acre-feet", "works for any farm". |
| **Length and time** | Over 30.0 s = not eligible for global judging; submission closes tonight. Render's free server can take a minute to wake. | Export 720 frames at 24 fps and check with `ffprobe`; warm the server or run the API locally before recording; if time runs short, submit the slide-based video from `docs/pitch.md` §3. |
| **Tone** | A "stereotypical farmer" can read as mockery. | Play him straight: competent, thoughtful, his own call at the end. The costume is the shorthand; the story respects him. |
