# Handoff: native iOS CropLytics (MapLibre)

Paste the starter prompt at the bottom into a new Claude session. This file is the spec. The app already exists under `apps/ios/`. Extend it. Do not start a second project, and do not put the website in a `WKWebView`.

`main` is `aae5f36` ("Web: tilt into the 3D stack during scroll and pinch"), on top of `e55209e`. Recent web commits add the numbered step flow, Ask, freeform outlook, the 3D stack for `pt_` / `my_` fields (`37bbcd4`, `8b6c399`, `ee228ef`, `27e6db1`), and the tilt that no longer kills the wheel or pinch (`aae5f36`). Android 1.1.1 (`284e901`) is the native phone layout to match. croplytics.xyz may still be serving an older build. Use the repo, not the live site.

The working tree may contain uncommitted Android Map3D experiments (`MainViewModel.kt`, `CropMap.kt`, `domain/StackBorrow.kt`). Leave them. They are not the iOS spec, and the ViewModel change has been failing to compile (see [Known gaps](#known-gaps)).

## 1. Product and farmer-first constraints

CropLytics is a California crop-rotation planner for growers and their advisers (NASA Space Apps 2026, "Field Shift"). It answers in fields, acres, inches, and acre-feet. Dataset names (NDVI, SMAP, GRACE, HLS) belong in a source line, not a heading.

Read and follow `.claude/skills/fieldshift-visual-design/SKILL.md` before changing any screen. Also `docs/ui-redesign-spec.md` (native mapping is section 3.8) and the "Farmer-first default" note in `PLAN.md`.

Rules that bite on iOS:

- One look: paper panels, Zilla Slab headings, Libre Franklin UI (already in `CropLytics/Resources/Fonts`), spot green as ink. Pills, floating rounded cards, pale tonal selection. No square 2px buttons, no solid-green header, no Inter/Roboto.
- Phone sheet: peek 128 pt, half about 52%, full. 20 pt top corners, grey grabber, 44 pt targets. Drag by transform; snap with the iOS drawer curve. At full, the content scrolls.
- Sections: Field now, Coming season, This field's year, Compare, Print for your adviser. Farmer default first; NASA, percentiles, and the 3D explanation sit behind More detail.
- Every number has a unit and a meaning. Example data says "Example numbers." Live data has no status pill.
- Map labels sit in a paper box with an ink edge. Selection on imagery is yellow `#ffd166`, not a fill. Reduced motion jumps the camera instead of flying.
- Dark mode uses the skill's dark tokens. The native apps may follow the system; the website does not.

## 2. What iOS already is

`apps/ios` is a real app: SwiftUI, iOS 17, Swift 6, XcodeGen (`project.yml`), `@Observable` models, offline-first `FieldRepository`, the five sections, date and replay, layers, Compare re-score, PDF share, fixtures, and unit tests. `apps/ios/README.md` is the build and App Store note. Two things are the wrong map:

| Today | Replace with |
|---|---|
| `Features/Shell/FieldsMap.swift` uses MapKit `.imagery` | MapLibre Native, same style and layers as Android `CropMap.kt` |
| `Features/DrillDown/DrillDownView.swift` is a SceneKit cover opened from a cube button | The stack drawn on the live map. Fill-extrusion height tracks zoom. Pitch tracks zoom while a pinch is in progress. Remove the cover once that works. |

Keep the shell (`RootView`, `BottomSheet`, `AppModel`, `FieldSession`, `Domain/*`, `Design/*`). The domain builders already match the farmer-first copy. Do not rewrite them to chase the website.

Android does **not** load the site in a WebView. iOS must not either.

## 3. Android architecture (the native reference)

Single-module Compose app, `apps/android`, application id `app.croplytics`, version 1.1.1 (`versionCode` 3). JDK 17, `compileSdk` 36, `minSdk` 26. MapLibre Android `org.maplibre.gl:android-sdk` **11.13.5**.

```
ui/app/        MainScreen, MainViewModel, chrome, pick list
ui/panels/     Field now, Coming season, Year, Compare, Print
ui/map/        CropMap (MapLibre), pins, overlay labels
ui/components/ pills, charts, status
ui/theme/      tokens, Zilla Slab, Libre Franklin
domain/        pure Kotlin: Map3D, calendars, answers, BC
data/          Retrofit, Room, file store for daily + grid, DataStore water limits
```

`MainViewModel` holds selection, tab, viewing date, layers, and compare tuning. Camera commands are a `Channel` (`FlyToField` card / drill / year, home, zoom, north, toggle 3D), not part of the panel state, so a pan does not recompose the sheet. `onCamera` only flips `drilledFlag` when zoom crosses 13.4.

API base is `https://croplytics-app.onrender.com/api/` (`BuildConfig.API_BASE_URL`). Override with `-PapiBaseUrl=`. A saved copy younger than 10 minutes skips the network; otherwise the saved copy shows while the server is asked. No answer for 3.5 s shows "Waking the server, up to a minute". A 404 is "Not on the server for this field yet". `POST /score` waits 450 ms after the water limit stops moving.

Release signing reads `~/.croplytics/keystore.properties` (or `CROPLYTICS_KEYSTORE_PROPS`). Missing file means an unsigned release. Play listing is not set up. Details: `apps/android/README.md`.

Map interactions that shipped:

- Esri World Imagery raster plus OpenFreeMap roads, boundaries, and place labels. No API key. Attribution stays on.
- Pan, pinch-zoom, rotate, two-finger tilt. Max pitch 70°.
- A pin per field. Tap the pin or the field outline (`field-hit`) to open it. Selected outline is `#ffd166` on a dark casing.
- Fly to a field at zoom 10.6, pitch 0 (card). "Look under the field" flies to zoom 15.15 if the field is under 45 ha, otherwise 14.5, pitch 60, bearing −24, center nudged south. Year mode is that zoom minus 0.75 and pitch 52.
- Footprints for SMAP, GRACE-FO, IMERG, and a line grid for field-scale layers. BC reserve outlines are context only (dashed, never a meaning-bearing fill of the analysis).
- Deep link `croplytics://field/<id>?tab=<0-4>` (0 now, 1 season, 2 year, 3 compare, 4 print). iOS does not register this yet. Add the same URL type.

Android does **not** ship tap-anywhere or drawing a field. Those exist on the web and in the API. An uncommitted `StackBorrow` helper is the start of borrowing a nearby prepared field's grid for `pt_` / `my_` ids. Do not wait for that patch to compile.

Compare and Coming season are in both native apps. Ask is web-only (`GET /api/chat/status`, `POST` from `frontend/app/src/api.ts` `askChat`). It is not a first milestone.

## 4. Parity checklist

Do these in order. Stop and run the app on a simulator after each map step.

1. **MapLibre map under the existing sheet.** Same home (`37.35, -119.9`, zoom 5.75), same style JSON as the `STYLE` constant in `apps/android/.../ui/map/CropMap.kt`. Pins, outlines, tap to open, fly card / home, layer footprints, yellow selection. Bottom inset follows the sheet.
2. **In-map 3D stack.** Port `domain/Map3D.kt` to a pure Swift type with tests (zoom window, extrusion heights, footprint miles, label words). Feed `GET .../grid`, the calendar, and the regional series. Fill-extrusion layers: cells, SMAP slab, GRACE slab, posts, ground shadow. Heights are style expressions on zoom, not a one-shot SceneKit scene.
3. **Pinch and the zoom buttons drive pitch.** See [3D requirements](#6-3d-drill-down). The cube button calls the drill flight. Delete `DrillDownView` when the stack is readable on the map.
4. **Camera stays off the panel state.** Mirror Android: a command stream for flights, and a drilled flag that updates only when the threshold flips.
5. **Deep link** `croplytics://field/<id>?tab=`.
6. **Freeform fields, native gestures.** After the stack works:
   - Tap or long-press empty map: `GET /api/analyze?lat=&lon=` (or `POST /api/analyze`). Id `pt_<n|s><lat×1e4>_<e|w><lon×1e4>`. Open the sheet immediately with skeletons. Show only `sections` that are `ready`. Hide `not_computed`. One quiet line for `unavailable`. A 200 m square is said on the map and in the id line. Non-farmland gets one notice. If `analysis.matches_preset` is a registry id, open that field instead.
   - Draw: rectangle, polygon, circle, freehand, add another part, cut a hole. `POST /api/my-fields {name, geometry}` with a GeoJSON Polygon or MultiPolygon (limits in the API section). The id is the field (`my_…`). Store ids on device. Rename or redraw is a new id. Delete forgets the id.
   - 3D for those ids: use the field's own grid when `GET .../grid` exists; otherwise shift the nearest prepared California field's grid onto this centroid (web `nearestCaPreset` / `mockCells`, and the idea in the uncommitted `StackBorrow.kt`). Say when the stack is borrowed.

Screens already on iOS that must keep working: pick list with search and rice / forage / BC chips, Field now, Coming season, This field's year (replay on the map), Compare with a saved water limit and `POST /score`, Print as one Letter PDF, More detail, waking and offline banners, BC First Nations and reserve outlines.

## 5. Recommended stack

**SwiftUI + MapLibre Native iOS 7.0.0**, wrapped in `UIViewRepresentable`.

Package (binary XCFramework, no plugin API):

```
https://github.com/maplibre/maplibre-gl-native-distribution
```

Product `MapLibre`, `import MapLibre`, view `MLNMapView`. Pinned release **7.0.0** (28 Oct 2026, minimum iOS 15.5). The app's deployment target is already iOS 17. Skip the `2026.11.x-globe` pre-releases. Docs: <https://maplibre.org/maplibre-native/ios/latest/documentation/maplibre-native-for-ios/gettingstarted/>.

Why this and not the others:

- **MapLibre** is what Android uses. One style JSON, the same Esri and OpenFreeMap sources, real `fill-extrusion`. BSD license, no token.
- **MapKit** (current iOS map) cannot extrude data polygons. `.imagery(elevation: .realistic)` is terrain, not the crop / SMAP / GRACE stack.
- **SceneKit** (current drill-down) is a separate diorama. It cannot sit in the satellite map or follow a pinch.
- **Mapbox Maps SDK** is the proprietary cousin. It needs a token and a different license for the same style spec.
- **WKWebView of croplytics.xyz** throws away the offline cache, the sheet, Dynamic Type, and the PDF share. The website's scroll-in 3D is still being fixed. Do not inherit that.

`MLNMapView` is UIKit and its callbacks are not Swift 6 `Sendable`. Keep every style and camera mutation on the main actor inside the representable. Do not reach for a SwiftUI DSL package; Android's pattern is a view plus GeoJSON sources, and that is the one to copy.

XcodeGen, in `project.yml`:

```yaml
packages:
  MapLibre:
    url: https://github.com/maplibre/maplibre-gl-native-distribution
    from: 7.0.0
```

and on the `CropLytics` target:

```yaml
dependencies:
  - package: MapLibre
    product: MapLibre
```

Then `cd apps/ios && xcodegen generate`. Commit the updated `project.pbxproj` with the app change (the project is committed so XcodeGen is optional for the next person).

## 6. API contracts

Base URL, trailing slash: `https://croplytics-app.onrender.com/api/`. iOS already uses it (`APIConfig.live`). Render's free instance sleeps; the client retries 429/502/503/504 and timeouts for about 90 s and shows the waking banner after a few seconds. Keep that.

Header `X-Data-Source` is `real`, `fixture`, `estimate`, `live`, `user`, or `catalog`. Trust it. Do not invent numbers for a 404.

Routes the native apps already call (paths under `/api/`):

| Route | Used for |
|---|---|
| `GET /locations` | Pin list and pick list. Query `family`, `county`, `region` exists; the apps fetch the list and filter on device. |
| `GET /locations/{id}` | One field. |
| `GET /locations/{id}/calendar?source=hls` | NASA calendar first. Fall back to the same path without `source` (Sentinel-2 / Landsat). |
| `GET /locations/{id}/calendar_ml` | Rule vs machine learning. |
| `GET /locations/{id}/nasa_now` | Today's SMAP, GRACE, IMERG, greenness. |
| `GET /locations/{id}/nasa_series` | One row per 10-day step from 2015. This is the slab time series. |
| `GET /locations/{id}/daily?from=2016-01-01` | About 2 MB. Rain, soil, groundwater history. |
| `GET /locations/{id}/grid` | About 2 MB. 30 m cells and greenness. 404 until the field pipeline has run. |
| `GET /locations/{id}/strategies` | Rotations. |
| `POST /locations/{id}/score` | Body `{allocation, weights?, scenario?: {dT_c, dP_pct}}`. Acre-feet per acre. Cache per body. |
| `GET /locations/{id}/outlook` | Coming season. `pt_` / `my_` may be a quiet gap, not a spinner. |
| `GET /locations/{id}/models`, `/openet`, `/water_seen`, `/stress`, `/insurance` | More detail. 404 is allowed. |
| `GET /locations/{id}/first_nations` and `.../reserves.geojson` | BC only. California is 404. |
| `GET /glossary` | Plain-language entries. |
| `GET /iss/{id}/iss.json` | Host root, not under `/api`. Astronaut photo. |

Freeform and tap (web + API, not in the Android UI yet). Full notes: `backend/api/README.md` "Analyse any location" and "My fields".

| Route | Contract |
|---|---|
| `GET /api/analyze?lat=&lon=` or `POST /api/analyze {lat, lon}` | Live location payload, `_source: "live"`. 422 bad coordinates, 429 with `Retry-After`, 504 after 45 s. Cold call is a few seconds. |
| `GET /api/analyze/{pid}/status` | Does not compute. |
| `GET /api/locations/{pt_id}` and `/{pt_id}/daily`, `/strategies`, `POST /score` | Same as a preset for those four. Any other sub-route is 404 "not computed for tapped points". |
| `POST /api/my-fields {name, geometry}` | Polygon or MultiPolygon. Caps: 20 parts, 20 holes per part, 400 corners, 0.5–2000 ha, no self-crossing rings, no overlapping parts. 422, 429, or 504 after 50 s. |
| `GET /api/my-fields/{id}`, `GET /api/my-fields?ids=` | Decode the id. `ids` does no upstream calls (max 100). |
| `GET /api/locations/{my_id}`, `/strategies`, `/daily`, `POST /score` | Work. Other sub-routes 404 "not computed for user-drawn fields". |

`sections.<name>.status` is `ready | not_computed | unavailable | error`. Tier 1 (boundary, county, weather, daily, crop history, family, soil, water, strategies) is computed on the tap. Tier 2 (IMERG, SMAP, GRACE, calendar, grid, outlook, …) is `not_computed` for points. OpenET is `unavailable`.

Example water limits, already in the iOS domain: Colusa and rice 5.0 acre-ft/acre, Kings and forage 3.0, labelled "example, change to yours".

Thumbnails today are `MKMapSnapshotter`. After MapLibre lands, cut them from Esri `MapServer/export` the way Android does (`FieldImagery.kt`), with the outline drawn on top, and keep the disk cache.

## 7. 3D drill-down

Source of truth for the geometry and the words: `apps/android/.../domain/Map3D.kt` and `frontend/app/src/MapView.tsx`. Copy the numbers. Do not invent a new stack.

Zoom window: `Z0 = 12.5`, `Z1 = 14.2`. Fraction

```
f = clamp((zoom - (Z0 - 0.3)) / (Z1 - Z0), 0, 1)
```

so the tilt starts just before the slabs leave the ground.

- Pitch `f * 58` degrees. Bearing `-22 * f` degrees while `f > 0`.
- Apply that only when the selected field's centroid is on screen (about a 64 pt margin) and the user is pinching, wheeling, or using the zoom buttons. A programmatic `flyTo` sets its own pitch and must not be overwritten mid-flight.
- Fill-extrusion `base` and `height` are zoom interpolations: 0 at `Z0`, the feature's `b` / `h` at `Z1`. Cell layer min zoom 11.2. Posts from `Z0 + 0.4`, slabs from `Z0 + 0.1`. Shadow fill opacity 0 at `Z0` to 0.42 at `Z1`.
- Three slabs, bottom to top: GRACE-FO groundwater (wide pad, pink family), SMAP root-zone soil moisture (tighter pad, blue family), then the 30 m cover cells coloured by greenness. Corner posts connect them when more than one layer is on. Layer toggles match `MapDatasets.DEFAULT_ON`: HLS, SMAP, and GRACE on; IMERG, MODIS, ECOSTRESS off.
- Labels are paper boxes at the slab's right-hand corner, in grower words ("Soil moisture in the root zone", "Wetter than usual (84th percentile)", "Basin-wide signal, not your own well"). Project them with altitude. Nothing under 13 pt.
- "Drilled" (hint can hide, stack reads as 3D) when zoom is past about 13.4 and a field is selected. Android uses `zoom > 13.4`. The website uses `zoom > 13.05` for the hint. Use 13.4 so the flag matches the native app.
- Reduced motion: set pitch and zoom in one jump. No decorative spin.

**Gesture bug.** `setPitch` / `setBearing` / `jumpTo` / `setCamera` during a pinch calls the equivalent of `map.stop()` and the fingers die before the stack opens. `aae5f36` fixes that on the web by writing `map.transform.pitch` and `.bearing` (MapLibre GL JS) and repainting, and by painting stand-in squares on the outline immediately. Read that commit. Do not wait for a deploy of croplytics.xyz.

On iOS, `MLNMapView.setCamera` and `camera =` from inside the pinch or region-change callback will cancel the gesture the same way. Android's uncommitted `tiltForDrill` assigns `cameraPosition` inside `onCameraMove` while a gesture is active. That is the bug. Do not port that assignment.

What to do instead:

1. Put the rising of the slabs entirely in style expressions on zoom. That part does not need a camera write, and it is the thing the grower sees move with their fingers.
2. Change pitch and bearing only in a way you have verified does not end the pinch. Try, on device or simulator, in this order: the map's raw transform if 7.0.0 exposes it without `jumpTo`; otherwise apply the tilt when the gesture ends and on zoom-button taps, and file a one-line note in this file if a mid-pinch tilt cannot be done without `setCamera`. A stack that rises during the pinch and tilts as soon as the fingers lift is acceptable. A pinch that dies is not.
3. Confirm with a real pinch into `car_colusa_rice` and a small field (under 45 ha): the outline stays under the fingers, the cells grow, the two slabs separate, and a second pinch still zooms.

## 8. Project scaffold (already done)

You do not create a new Xcode project.

```sh
# once, only if you edit project.yml
brew install xcodegen
cd apps/ios && xcodegen generate

# build and test. This Mac's simulators may be iOS 17.5, not 18.
xcodebuild -project CropLytics.xcodeproj -scheme CropLytics \
  -destination 'platform=iOS Simulator,name=iPhone 16,OS=17.5' build
```

`project.yml` excludes `Assets.xcassets` because Xcode 16.4's asset compiler wanted an iOS 18 runtime this machine did not have. Leave that exclude until a machine has the runtime. App Store steps, the privacy manifest, and the font OFL files are already in `apps/ios/README.md`. Signing stays automatic. Do not set `DEVELOPMENT_TEAM` until someone has an Apple Developer account. No certificates exist in the repo.

Info.plist already has ATS-friendly HTTPS, `ITSAppUsesNonExemptEncryption` false, and the bundled fonts. Add the `croplytics` URL type when you add the deep link. Do not add a location usage string unless a feature actually reads GPS. Tap and draw use the map coordinate, not Core Location.

After MapLibre is linked, the first screen is still `RootView`: map full bleed, top bar, sheet, tab bar. Swap the `Map` inside `FieldsMap` for the representable. Keep the SwiftUI pins only until symbol layers replace them. Selection yellow and paper labels move onto the style or onto projected overlays, the way `MapOverlays.kt` projects stack labels.

## 9. Non-goals

- Do not wrap croplytics.xyz, the Render frontend, or `frontend/app` in `WKWebView` / `SFSafariViewController`.
- Do not wait for croplytics.xyz to redeploy the tilt fix (`aae5f36` is already on `main`), and do not block on the Android `MainViewModel` compile.
- Do not edit the dirty Android or web files as part of this task.
- Do not add Ask, the salmon panel, or a second visual theme.
- Do not retune copy, thresholds, or the water-limit examples. The domain builders are the copy.
- Do not publish to the App Store or create an Apple Developer account.
- iPad split view is later. Ship the iPhone layout.

## Known gaps

- **Website deploy.** `aae5f36` commits the scroll and pinch tilt in `frontend/app/src/MapView.tsx`. The public site can lag that commit. Port the committed file, not whatever croplytics.xyz is doing today.
- **Android WIP, not on `e55209e`.** `MainViewModel` around the new `fieldLoads` combine (about line 248 in the dirty file) builds `listOf(...)` from `LoadState<Daily>`, `LoadState<CellGrid>`, and other unrelated types. `LoadState` is invariant, so that list does not type-check. `StackBorrow.kt` is the borrow/shift idea and is also uncommitted. Geometry that *is* committed and safe to port is `domain/Map3D.kt`.
- **iOS asset catalog** stays excluded on this machine. See the README.
- **Grid weight.** `GET .../grid` and `GET .../daily` are about 2 MB. Android stores them as files. iOS already has `ResponseCache`. Do not decode the grid on the main actor.

## Starter prompt

```
You are building the native iOS CropLytics app in /Users/caide/Documents/nasa-hacks/apps/ios. Read apps/ios/HANDOFF.md and .claude/skills/fieldshift-visual-design/SKILL.md before editing. The app is already SwiftUI (iOS 17, Swift 6, XcodeGen). Keep it. Do not create a second project.

Goal: the iPhone app runs on MapLibre Native the way apps/android runs on MapLibre Android. Same Esri + OpenFreeMap style, pins, field tap, fly-to-field, and the zoom-driven 3D stack (30 m cover cells, SMAP soil-moisture slab, GRACE-FO groundwater slab). Pitch follows zoom while a pinch is happening, and the pinch must not die. The web fix is commit aae5f36 (write the live transform; do not call setPitch mid-gesture). Do not wait for croplytics.xyz to redeploy, and do not load the site in a WKWebView.

Start here:
1. Add https://github.com/maplibre/maplibre-gl-native-distribution at 7.0.0 (product MapLibre) to apps/ios/project.yml and run xcodegen.
2. Replace MapKit in Features/Shell/FieldsMap.swift with an MLNMapView representable. Copy the style JSON from apps/android CropMap.kt. Selection outline #ffd166. Attribution stays on.
3. Port apps/android domain/Map3D.kt to pure Swift and unit-test the zoom fraction, extrusion heights, and footprint wording. Drive fill-extrusion from zoom expressions (Z0 12.5, Z1 14.2, pitch = f*58, bearing = -22*f). Do not assign the camera from inside the pinch callback; that cancels the gesture (the bug Android's uncommitted tiltForDrill copies).
4. Verify on the iOS 17.5 simulator: open car_colusa_rice, pinch in, cells and both slabs rise, a second pinch still zooms. Then remove the SceneKit DrillDownView cover.
5. Only after that, add tap-anywhere (GET /api/analyze) and drawing a field (POST /api/my-fields). Android does not have those screens yet. The API section of HANDOFF.md is the contract.

Do not edit the uncommitted Android MainViewModel / CropMap / StackBorrow files or the web app. Do not commit unless asked. API base is https://croplytics-app.onrender.com/api/. Farmer-first copy stays in the existing Domain builders.
```
