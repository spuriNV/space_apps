# CropLytics for Android

A native Android app for CropLytics, the crop-rotation planner for California growers and their advisers, built on NASA Earth data (NASA Space Apps 2026, "Field Shift"). It reads the live API at `https://croplytics-app.onrender.com/api` (see `backend/api/README.md`) and follows the farmer-first rules in `.claude/skills/fieldshift-visual-design` and the "Farmer-first default" decision in `PLAN.md`.

Screenshots: `design/screenshots/android/`.

## What it does

| Screen | What the grower sees first | Behind "More detail" |
|---|---|---|
| **Fields** | Search, then one row per field: satellite thumbnail with the outline, farmer-style name ("Rice field 3.5 miles east of Williams"), acres, this year's crop, county, and a one-line crop record | – |
| **Field now** | Still satellite map with the outline ("Open map" for a full map), then a visual summary (this year's bare/green/flooded strip, rain vs normal, water need vs limit, greenness, soil and groundwater percentiles), then at most 4 one-sentence answers, each with a source line | About this field, crops grown, how to read the strip, events, NASA data behind the field, crop-stress weeks, standing water, measured water use (OpenET), machine-learning check, crop insurance, every source |
| **Coming season** | 3 items: rain outlook (with drought), water in storage and allocations, next season's water need | Every 3-month outlook, the longest bare stretch and heavy-rain odds, the full outlook paragraph, what isn't published yet |
| **Compare** | Your water limit (editable, saved per field, "example, change to yours" until you change it), today's rotation, then the top 2 options as "You gain / You give up" in acre-feet and days; "See all options" | How the options are ranked (rule-of-thumb scores), how good the water estimate is (OpenET), what better/worse means |
| **For your adviser** | Pick the option, then "Share as PDF": a one-page US Letter summary drawn with `PdfDocument` and sent through the Android share sheet | – |

Every screen has loading skeletons, an error panel with "Try again", pull to refresh, and a "Waking the server, up to a minute" panel when the free Render server is asleep. Everything the app has fetched is saved on the phone, so a field opens offline with "Saved on <date>. Can't reach the server right now."

A deep link opens any field section directly: `croplytics://field/<id>?tab=<0-3>` (0 field now, 1 coming season, 2 compare, 3 for your adviser).

## Architecture

Single activity, Jetpack Compose and Material 3, MVVM with unidirectional data flow.

```
ui/            Compose screens (stateless *Content functions) + one @HiltViewModel per screen,
               each exposing a StateFlow<UiState>; events go up as plain callbacks
  fields/      Fields list and search
  field/       Field container: top bar, text tabs (3 dp spot-green indicator), HorizontalPager
  now/ season/ compare/ summary/ map/
  components/  Status (skeleton, waking, error, offline note), blocks, charts (Canvas), MapLibre map, thumbnails
  theme/       Bulletin palette tokens (light and dark), Zilla Slab + Libre Franklin, small radii
domain/        Pure Kotlin: payload -> farmer wording (names, units, answers, gain/give-up, PDF content)
data/
  remote/      Retrofit + kotlinx.serialization API and DTOs (every field optional)
  local/       Room cache (one JSON row per response, with the time it was saved); DataStore water limits
  repository/  FieldRepository: offline-first flows of LoadState (Loading, Waking, Ready, Failed)
di/            Hilt module: OkHttp (75 s read timeout for the sleeping server), Retrofit, Room, DataStore
```

**Data flow.** A ViewModel combines repository flows (location, calendar, NASA readings, rotations, outlook, the saved limit) and maps them through `domain/` builders into one UI state. `DefaultFieldRepository.cached()`:
1. shows a saved copy younger than 10 minutes without calling the server;
2. otherwise shows the saved copy (marked refreshing) and asks the server;
3. with nothing saved and no answer after 3.5 s, emits `Waking`;
4. on failure keeps the saved copy marked offline, or emits `Failed(NoConnection | NotAvailable | Server)`.

Concurrent requests for the same key share one network call (four tabs, one fetch). A 404 (a route the live server doesn't have yet, such as `stress` or `water_seen`) becomes "Not on the server for this field yet", never a crash.

**Compare re-scoring.** The limit slider updates the screen at once, is saved to DataStore after 400 ms, and `POST /api/locations/{id}/score` runs once the value has been still for 450 ms. Scored results are cached per limit. If re-scoring fails, the server's default ranking is shown with a note.

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

**Tests** (`app/src/test`):
- `data/DefaultFieldRepositoryTest`: MockWebServer with real API payloads. First load and save, the fresh-cache shortcut, a stale copy then the fresh one, offline with a saved copy, 404 vs 5xx, the waking state on a slow server, the shared in-flight request, and the score POST body and per-limit cache.
- `domain/BuildersTest`, `domain/FieldNamesTest`: farmer wording, units, the 4 answers, the 3 coming-season items, gain/give-up, limit fit, the adviser summary and thumbnail geometry.
- `ui/ViewModelsTest`: the ViewModels against a fake repository with coroutine test dispatchers (search, waking/offline/error, retry, saved vs example limit, debounced save and re-score, failed re-score, "See all options").
- `ui/ScreensUiTest`: Compose UI tests under Robolectric (the field list and opening a field, the waking panel, error and "Try again", and Compare's limit buttons and "See all options").

Fixtures in `app/src/test/resources/fixtures/` are trimmed copies of the live API's responses for the Colusa rice field (14 Nov 2026).

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

## Not in this app

To match the web app's farmer-first scope (`PLAN.md`): no 3D view, no date picker or year replay, no "your priorities" weighting or what-if sliders on Compare, and no news timeline.
