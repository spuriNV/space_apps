# Releasing CropLytics on Google Play

Package `app.croplytics`, version 1.3.0 (versionCode 5). Full click-path: `checklist.md`.

## Build the AAB (on the Mac)
```sh
cd apps/android
./gradlew bundleRelease     # app/build/outputs/bundle/release/app-release.aab
```
It signs with the upload key named in `~/.croplytics/keystore.properties` (keystore kept outside git). Bump `versionCode` in `app/build.gradle.kts` for every upload.

## Steps
1. Create the app in Play Console (free, App). Enrol in **Play App Signing** (default): Google holds the signing key, you upload with your upload key. Back up the keystore and passwords.
2. **Internal testing** first: upload the AAB, add your own Gmail, install from the opt-in link, smoke-test.
3. **Closed testing**: a new personal account must have **at least 12 testers opted in for 14 continuous days** before it can apply for production. Then Dashboard > Apply for production.
4. Fill App content using `data-safety.md` (Data safety, content rating, target audience 18+, ads: none, app access: no login).
5. Check https://croplytics.xyz/privacy.html loads, then roll out to production.

## Where each asset goes
| Asset | Console location |
|---|---|
| `listing.md` name, short and full description (EN, and Spanish es-419 as a translation) | Grow users > Store presence > Main store listing |
| `icon-512.png` | Main store listing > App icon |
| `feature-graphic.png` (1024 x 500) | Main store listing > Feature graphic |
| `screenshots/*.png` (1080 x 2160, at least 2, up to 8) | Main store listing > Phone screenshots |
| `data-safety.md` | App content > Data safety, Content rating, Target audience, Ads, App access |
| Privacy policy URL `https://croplytics.xyz/privacy.html` (source `privacy.html`) | App content > Privacy policy |
| Contact website `https://croplytics.xyz` | Store settings > Contact details |
