# CropLytics for Android

A native Android app for CropLytics, the crop-rotation planner for California growers and their advisers, built on NASA Earth data (NASA Space Apps 2026, "Field Shift"). It reads the live API at `https://croplytics-app.onrender.com/api` (see `backend/api/README.md`) and follows the farmer-first rules in `.claude/skills/fieldshift-visual-design` and the "Farmer-first default" decision in `PLAN.md`.

Screenshots: `design/screenshots/android/`.

## What it does

A native port of the web app (`frontend/app`), screen for screen, in its phone layout and to `docs/ui-redesign-spec.md`.
The satellite map fills the screen edge to edge under a transparent status bar. A floating search bar ("Search fields or places") opens a full-screen search with the field list and crop filters. Thumb-sized map buttons sit above the sheet: viewing date, layers, 3D, north and home. The field lives in a draggable bottom sheet (128 dp peek with the field name and one key line, 48%, full) with a grabber and a collapse chevron, and its sections are scrollable pills inside the sheet. Back closes search, then collapses the sheet, then leaves the field. Since 1.1.1 the sheet is a custom anchored sheet (not `BottomSheetScaffold`), so touches outside it always reach MapLibre, and the camera is kept out of the screen state so map moves never recompose the panels.

| Part | What it shows |
|---|---|
| **Map** | Esri imagery with OpenFreeMap labels; pan, pinch-zoom, rotate, two-finger tilt. A pin for every field (tap to open), outlines, SMAP / IMERG / GRACE footprints, Map layers sheet with pixel sizes. Zooming in under a field tilts the camera and its 30 m cells rise as fill-extrusions coloured by greenness, with SMAP and GRACE-FO slabs, posts and labels. BC: reserve outlines as a context layer. |
| **Pick your field** | Search, Rice / Forage / British Columbia chips, satellite thumbnails with outlines, 2023 to now season strips, one notable line. |
| **Viewing date** | Menu > Viewing: Today, quick picks (last summer, last spring, 2023 floods, 2022 drought) and a month picker; a floating "Showing ... Back to today" pill. |
| **Field now** | Paper header (collapses on scroll) with action pills; glance card (season strip, rain, water need, greenness, soil and groundwater; readings count up, bars glide); five answers including soil composition. More detail: NASA data list with the ISS photo, About the ground, the last 3 seasons, events, Sources. BC: Working with First Nations. |
| **Coming season** | Winter rain, water supply (BC: watershed and irrigation orders), next season's need; More detail: outlooks, drought, reservoirs, allocations, snowpack, bare stretch, need by rotation. |
| **This field's year** | Typical year and one strip per season with rain, OPERA water and stress marks; rule vs machine learning; replay on the map; tap a cell to move the date. |
| **Compare** | The two best options (all with More detail), water limit (saved per field), weather replays, priorities and what-ifs re-scored by POST /score, gain / give up with range bars, See all options. |
| **Print** | One Letter page for the adviser; Share as PDF or Print (PdfDocument, Android print). |

Every part has skeletons, an error panel with "Try again", and "Waking the server, up to a minute" for the sleeping free server. Everything fetched is saved on the phone ("Saved on <date>"). Deep link: `croplytics://field/<id>?tab=<0-4>`.

## Architecture

Single activity, Compose and Material 3, MVVM with unidirectional data flow.

```
ui/app/        MainScreen (map + sheet + tabs), MainViewModel (selection, date, tabs, layers, compare tuning,
               map commands as a channel), chrome (search bar, map buttons, sheets), the pick list
ui/panels/     Field now, Coming season, This field's year, Compare, Print (LazyListScope builders)
ui/map/        CropMap (MapLibre), pin bitmaps, overlays (stack and footprint labels, controls, legend)
ui/components/ Redesign controls (pills, chips, segmented, disclosure, focus ring, count-up), charts, status
ui/theme/      Spec tokens (light and dark), Zilla Slab + Libre Franklin, reduce-motion flag
domain/        Pure Kotlin ports of the web's lib.ts, season.ts, bare.ts, nasa.ts and components
data/          Retrofit API, Room cache, file store for the 2 MB daily record and grid, DataStore water limits
```

**Data flow.** A ViewModel combines repository flows (location, calendar, NASA readings, rotations, outlook, the saved limit) and maps them through `domain/` builders into one UI state. `DefaultFieldRepository.cached()`:
1. shows a saved copy younger than 10 minutes without calling the server;
2. otherwise shows the saved copy (marked refreshing) and asks the server;
3. with nothing saved and no answer after 3.5 s, emits `Waking`;
4. on failure keeps the saved copy marked offline, or emits `Failed(NoConnection | NotAvailable | Server)`.

Concurrent requests for the same key share one network call (four tabs, one fetch). A 404 (a route the live server doesn't have yet, such as `stress` or `water_seen`) becomes "Not on the server for this field yet", never a crash.

**Re-scoring.** The limit slider updates the screen at once, is saved to DataStore after 400 ms, and `POST /api/locations/{id}/score` runs once the value has been still for 450 ms. Scored results are cached per limit. If re-scoring fails, the server's default ranking is shown with a note.

**Map and imagery.** MapLibre Native Android with an inline raster style on Esri World Imagery (no key, as in `CONTRACT.md`); the field outline is a yellow `#ffd166` line on a dark casing. List thumbnails are Esri `MapServer/export` images cut to a Web Mercator box around the field, with the outline drawn on top in Compose; Coil keeps them on disk for offline use.

**Accessibility.** All text in `sp` (follows the system font size; summary cells wrap), headings marked for TalkBack, every chart has a spoken sentence (`contentDescription`), 48 dp touch targets, explicit −/+ buttons next to the limit slider, live regions for the waking panel and the limit value, and a dark theme from the same tokens.

## Build, run, test

You need JDK 17 and the Android SDK (platform 36, build-tools 35). The Gradle wrapper (8.13) is checked in.

```sh
cd apps/android
export ANDROID_HOME=~/Library/Android/sdk
export JAVA_HOME=/path/to/jdk-17
./gradlew assembleDebug                 # app/build/outputs/apk/debug/app-debug.apk
./gradlew testDebugUnitTest             # unit + Robolectric Compose UI tests (JVM, no device)
./gradlew installDebug                  # onto a running emulator or phone
```

Use a local API instead of the live one with `./gradlew assembleDebug -PapiBaseUrl=http://10.0.2.2:8000/api/` (`10.0.2.2` is the host machine from the emulator; a non-HTTPS URL also needs a network security config).

**Tests** (`app/src/test`, 42): repository with MockWebServer (offline-first cache, waking, 404 vs 5xx, shared requests, HLS fallback, file store); the live field list parses (11 fields incl. BC); the web ports (clock, calendar, five answers, coming season, year, compare verdicts, the 3D stack, NASA list, brief); BC (watershed and orders, gap lines, rain-fed, First Nations, estimates); MainViewModel (filters, select-and-fly, date and replay, tabs, debounced re-score, saved limit, deep link); Compose UI tests under Robolectric.

Release: `./gradlew assembleRelease -Pabi=arm64-v8a` signs with the keystore named in `~/.croplytics/keystore.properties` (outside git).

## Releasing on Google Play (not done)

No accounts, keys or listings have been created. To publish:

1. **Google Play Console account**: a one-time US$25 registration, identity verification, and (for a new personal account) the closed-testing requirement before production.
2. **Upload key**: `keytool -genkeypair -v -keystore upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload`. Keep it outside git (`*.jks`, `*.keystore` and `keystore.properties` are git-ignored) and wire it in through a `signingConfigs { create("release") { ... } }` block that reads `keystore.properties` or CI secrets.
3. **Play App Signing**: enrol (the default for new apps); Google holds the app signing key and you upload with the upload key.
4. **Build an App Bundle**: `./gradlew bundleRelease` (R8 minify and resource shrinking are already on; check `proguard-rules.pro` with a release smoke test). Bump `versionCode` for every upload.
5. **Store listing**: app name, short and full description, the screenshots in `design/screenshots/android/`, a 512 px icon, a feature graphic, category (Business or Productivity), and contact email.
6. **Policy forms**: privacy policy URL (the app collects no personal data; it stores the field cache and water limits on the device only), Data safety form ("no data collected or shared"), content rating questionnaire, target audience (adults), and ads declaration (none).
7. **Target API**: Play requires a recent `targetSdk` (36 here); raise it as Google's yearly deadline moves.
8. **Testing tracks**: internal testing first, then closed testing, then production with a staged rollout.

Before a real release: move the API off the free Render plan (cold starts), add Esri's attribution and terms review for imagery use, and add crash reporting.

## Not in this app yet

The salmon panel (waiting for its `/salmon` route) and the web's 3D water-use mode (removed from the web too).
