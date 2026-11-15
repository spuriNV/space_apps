# CropLytics for iOS

A native iPhone app for CropLytics, the crop-rotation planner for California growers and their advisers, built on NASA Earth data (NASA Space Apps 2026). It reads the live API at `https://croplytics-app.onrender.com/api` and keeps the last answers on the phone, so a field you opened before still shows offline with a "Saved on <date>" note.

It mirrors the web app's farmer-first scope (PLAN.md, "Farmer-first default"). If the web app drops a feature, drop it here too.

| Tab | What it shows |
|---|---|
| Fields | Searchable list: satellite thumbnail with the field outline, farmer-style name, county, acres and this year's crop |
| Field now | Satellite map, then a summary (season strip, rain vs normal, water need vs limit, greenness, soil and groundwater percentiles), then 4 one-sentence answers |
| Coming season | 3 items: the rain outlook, water supply, next season's water need. Outlooks, not forecasts |
| Compare | Today's rotation vs the top 2 alternatives, as what you gain and give up in acre-feet and days; the water limit is editable, saved per field, and re-scored with `POST /api/locations/{id}/score`; "See all options" |
| Summary | One US Letter page for the adviser, rendered to PDF with `ImageRenderer` and shared with `ShareLink` |

Every field tab ends with **More detail**: the NASA data behind the field, the rule vs machine-learning check, crop-stress weeks, standing water, county crop insurance and a glossary, plus the screen's own extras. It loads only when opened.

Screenshots: `design/screenshots/ios/`.

## Architecture

```
CropLytics/
  App/          entry point, AppEnvironment (dependency container), AppModel (tabs, chosen field), RootView (TabView + NavigationStack per tab)
  Networking/   Endpoint (every route), APIClient (URLSession, retries while the free server wakes), AppError, ServerStatus
  Models/       Codable payloads: FieldLocation, NasaNow, FieldCalendar, Strategy, Outlook, ModelReport, Glossary, ...
  Data/         FieldRepository (offline-first streams), ResponseCache (file cache), LoadState, WaterLimitStore, ThumbnailStore
  Domain/       pure functions: grower units and dates, farmer-style names, calendar maths, and the builders that turn
                payloads into answers (FieldNowBuilder, ComingSeasonBuilder, CompareBuilder)
  Features/     one folder per screen: an @Observable view model and its SwiftUI views
  Design/       palette and type tokens (from the fieldshift-visual-design skill) and shared components (charts, answer rows, banners)
  Resources/    fonts (OFL), app icon PNGs, privacy manifest, JSON fixtures, asset catalog (see "Known limits")
```

- **SwiftUI, iOS 17+, Swift 6 language mode** with complete strict concurrency.
- **Observation**: every view model is `@MainActor @Observable`; screens create theirs in `.task(id: field.id)`.
- **Dependency injection through the environment**: `AppEnvironment` holds the repository, water-limit store, thumbnail store, server status and the "today" clock. The app uses `.live()`; UI tests and previews use `.fixtures()`, which serves `Resources/Fixtures/*.json` through a `URLProtocol` with no network.
- **Typed API client**: `Endpoint` lists the routes; `APIClient` builds requests, retries 429/502/503/504 and timeouts for up to 90 s with backoff (Render's free plan takes about 50 s to wake), and maps failures to plain `AppError`s. After 3 s without an answer it reports a slow request, and every tab shows **"Waking the server, up to a minute"**.
- **Offline-first repository**: `stream(_:)` yields the saved copy from disk at once (marked with its date), then the live answer. Recent answers sit in memory for 10 minutes and concurrent requests for the same route are shared. Saved copies live in Application Support as binary plists, excluded from iCloud backup. If a refresh fails, the saved copy stays on screen with "Saved on 14 Nov 2026. You're offline, so this is what you saw last time." A file cache was chosen over SwiftData because the payloads are read whole and never queried.
- **Farmer-first copy** is built in `Domain/` as pure functions ported from the web app (`FieldNow.tsx`, `ComingSeason.tsx`, `ComparePanel.tsx`), so the wording and the rules match: bare = greenness below 0.2 and not under water; a gain counts only when the likely ranges don't overlap; example water limits (Colusa 5.0, Kings 3.0, rice ground 5.0, forage ground 3.0) are labelled "example, change to yours".
- **Maps**: MapKit `Map` with `.imagery` style and the outline as a `MapPolygon` in the selection yellow. List thumbnails are `MKMapSnapshotter` images with the outline drawn on, cached on disk.
- **Charts**: Swift Charts for the meters, percentile track, NOAA lean, reservoir storage, water need vs limit and the today-vs-option ranges. The season strip uses `Canvas` so "no clear view" can be hatched, as on the web.
- **Accessibility**: Zilla Slab and Libre Franklin are bundled (`UIAppFonts`) and every style is `relativeTo:` a text style, so Dynamic Type scales them; charts and strips have VoiceOver sentences; colours have light and dark variants that keep the skill's contrast targets.
- **Loading and errors**: `.redacted(reason: .placeholder)` layouts while loading; `ContentUnavailableView` with "Try again" when nothing could be loaded; "Not on the server for this field yet" for routes that answer 404.

## Build, run and test

You need Xcode 16 or later. The project is generated with [XcodeGen](https://github.com/yonaskolb/XcodeGen) from `project.yml`; the generated `CropLytics.xcodeproj` is committed, so you can open it without XcodeGen. After editing `project.yml`:

```sh
brew install xcodegen          # once
cd apps/ios && xcodegen generate
```

Run: open `CropLytics.xcodeproj`, pick an iPhone simulator, Run. From the command line:

```sh
cd apps/ios
xcodebuild -project CropLytics.xcodeproj -scheme CropLytics \
  -destination 'platform=iOS Simulator,name=iPhone 15,OS=17.5' build
xcodebuild -project CropLytics.xcodeproj -scheme CropLytics \
  -destination 'platform=iOS Simulator,name=iPhone 15,OS=17.5' -parallel-testing-enabled NO test
```

Launch arguments for demos and screenshots: `-initialField car_colusa_rice -initialTab now|season|compare|summary|fields`. `-ui-testing` runs on the bundled fixtures; add `-slow-server` to see the wake-up banner.

Tests:
- `CropLyticsTests` (Swift Testing): the API client against a `URLProtocol` stub (decoding, URLs, the POST body, retry while waking, give-up, 404 without retry, offline, changed payload shape), the offline-first repository (saved copy with its date, error without one, score fallback), the view models on the fixtures (field search and opening, Field now answers, Coming season items, Compare top 2 and per-field limit with re-scoring, one-page PDF), and the unit and wording helpers.
- `CropLyticsUITests` (XCTest): pick a field, read Field now, change the limit on Compare, make the summary; search the field list.

Fixtures in `CropLytics/Resources/Fixtures` are trimmed copies of the live API's answers for the two original fields (14 Nov 2026).

## Known limits

- **Asset catalog not in the build on this Mac.** Xcode 16.4's asset compiler needs an iOS 18 simulator runtime and this machine has only 17.4 and 17.5, so `Resources/Assets.xcassets` (1024 pt icon, accent colour, launch colour) is excluded in `project.yml` and the icon ships as `CFBundleIconFiles` PNGs. On a machine with the iOS 18.5 runtime, remove the exclude and set `ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon`; App Store builds need the catalog icon. To build against the 17.5 runtime with Xcode 16.4, the SDK was pointed at it with `xcrun simctl runtime match set iphoneos18.5 21F79` (undo with `xcrun simctl runtime match set iphoneos18.5 --default`).
- iPhone only (`TARGETED_DEVICE_FAMILY = 1`); the layouts would need a sidebar for iPad.
- Answers are for today only; the web app's date control and "This field's year" are not in the phone app.

## App Store release: what it would take

Nothing here has been set up; no accounts or certificates were created.

1. **Apple Developer Program** membership (USD 99 a year) for an individual or the team's organisation (organisations need a D-U-N-S number).
2. **Bundle ID and signing**: register `org.croplytics.CropLytics` (or the team's own reverse domain) in Certificates, Identifiers & Profiles; set `DEVELOPMENT_TEAM` in `project.yml`; keep automatic signing, or create an Apple Distribution certificate and an App Store provisioning profile for CI.
3. **Icon and assets**: re-include `Assets.xcassets` (see Known limits) so the 1024 pt App Store icon is compiled.
4. **Privacy**: `Resources/PrivacyInfo.xcprivacy` declares no tracking, no collected data, and the one required-reason API used (UserDefaults, reason CA92.1). The App Privacy answers in App Store Connect are "Data Not Collected". A privacy policy URL is still required.
5. **Export compliance**: `ITSAppUsesNonExemptEncryption` is `false` (HTTPS only).
6. **App Store Connect**: create the app record, then add the name, subtitle, description, keywords, support URL, category (Weather or Productivity), age rating, and 6.7" and 6.5" iPhone screenshots (`design/screenshots/ios/` is a start).
7. **Upload and review**: Product > Archive in Xcode (or `xcodebuild archive` plus `-exportArchive`), upload to App Store Connect, test with TestFlight, then submit. The live server should be on a paid Render plan first, so reviewers don't wait for a sleeping server; the app already explains the wait.
8. **Data credits and licences**: the fonts are SIL OFL (licences in `Resources/Fonts`). NASA, USDA, NOAA, CDEC and Reclamation data are public; map imagery is Apple's, under the MapKit terms.
