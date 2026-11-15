# Data safety form: answers for CropLytics 1.2.0 (app.croplytics)

Based on the code in `apps/android/app/src/main` (read 15 Nov 2026). Play Console > Policy and programs > App content > Data safety.

## What the app actually does

- Permissions in AndroidManifest.xml: `INTERNET` and `ACCESS_NETWORK_STATE` only. No location, no microphone, no camera, no contacts, no storage, no ad ID.
- Network (all HTTPS): reads `https://croplytics-app.onrender.com/api` (Retrofit GET for fields and their data by field id; one POST that sends the water limit, priority weights and a what-if scenario for a field id). Map tiles from `server.arcgisonline.com` (Esri) and `tiles.openfreemap.org`; field thumbnails from Esri.
- On the phone: a Room cache of server answers, a file store for the daily record, and DataStore holding the water limit per field. Cloud backup of the database is excluded. The PDF for the adviser is shared through FileProvider, only when the user taps Share.
- No SDKs for ads, analytics, crash reporting or sign-in. No accounts. No purchases.
- The app does not send the user's coordinates. It has no tapped or drawn fields and no voice input; those exist only on the website.

## Section 1: Data collection and security

| Question | Answer |
|---|---|
| Does your app collect or share any of the required user data types? | **Yes** (see the decision below; "No" is also defensible) |
| Is all of the user data collected by your app encrypted in transit? | **Yes** (HTTPS only) |
| Do you provide a way for users to request that their data be deleted? | **Yes**: clear storage or uninstall removes everything on the phone; nothing is held on a server account. Email caiden.merklin@gmail.com for anything else. (No account exists, so no deletion URL is required.) |

### DECISION for the owner: how to declare the field ids and water limit

The app sends a field id and, when the slider is used, a water limit and priorities. None of it identifies a person, and there is no account. Recommended, cautious answer:

| Data type | Collected | Shared | Optional | Purpose |
|---|---|---|---|---|
| App activity > Other actions (field viewed, water limit and priorities used for scoring) | Yes | No | No (needed for the feature) | App functionality |

Everything else on the Data types list: **not collected**: location (approximate and precise), personal info, financial info, health, messages, photos and videos, audio, files and docs, calendar, contacts, web browsing, device or other IDs, app info and performance (no crash logs).

Alternative: answer "No data collected." Google's own guidance lets you skip data that is processed only ephemerally or is not tied to a person, but the server does see the IP address of every request, so the cautious table above is safer. Third-party tile servers (Esri, OpenFreeMap) also see the IP address and the map area when tiles load. Treat them as service providers acting for the app, so "Shared: No".

## Section 2: Other statements

| Question | Answer |
|---|---|
| Data sold | No |
| Data used for advertising or marketing | No |
| Data used for tracking across apps | No |
| Data shared with third parties | No |
| Ads | No ads |

## Website features (only if the website is covered)

Play's form covers the app only. For information, the website at croplytics.xyz additionally sends tapped or drawn field coordinates, an optional chat question (to the DeepSeek API) and optional short voice clips (transcribed on our server, not stored). None of this is in the Android app. The privacy policy (`privacy.html`) covers both.

## Other App content declarations

| Form | Answer |
|---|---|
| Privacy policy | https://croplytics.xyz/privacy.html |
| App access | All functionality is available without login or special access. Select "All functionality is available without special access". |
| Ads | No, the app does not contain ads |
| Content rating (IARC questionnaire) | Category: Utility, Productivity, Communication or other. Answer **No** to every question (violence, sexual content, language, controlled substances, gambling, user-generated content, location sharing, purchases, web browsing). Expected rating: Everyone / PEGI 3. |
| Target audience and content | Age group: **18 and over** only. Not designed for children. No appeal to children. |
| News app | No |
| COVID-19 contact tracing or status | No |
| Government app | No |
| Financial features | None |
| Health features | None |
| Data deletion URL | Not required (no accounts) |
| Advertising ID | Not used. Answer "No" (the app does not use the AD_ID permission). |
