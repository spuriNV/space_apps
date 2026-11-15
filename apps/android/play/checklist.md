# Play Console click-path for CropLytics (app.croplytics)

Files are in `apps/android/play/`. Do these in order. Build the AAB separately (`./gradlew bundleRelease`, versionCode 4, versionName 1.2.0).

## 1. Create app
1. play.google.com/console > **Create app**.
2. App name: `CropLytics`. Default language: English (United States).
3. App or game: **App**. Free or paid: **Free**.
4. Tick the Developer Program Policies and US export laws declarations. **Create app**.

## 2. Play App Signing
1. Left menu > **Test and release > App integrity > App signing** (or it is offered on your first release).
2. Choose **Use Play App Signing** (default). Google holds the app signing key.
3. You upload the AAB signed with your upload key (`upload.jks`, kept outside git). Keep a backup of the upload key and its passwords.

## 3. Testing path (new personal account rule)
1. **Internal testing**: Test and release > Testing > Internal testing > **Create new release** > upload the `.aab` > release notes > Save > Review release > **Start rollout**. Add your own Gmail under Testers and install from the opt-in link to smoke-test.
2. **Closed testing**: Testing > Closed testing > Create track > **Create new release** with the same or a newer AAB. Under Testers create an email list with **at least 12 testers** (use real Gmail accounts, ask them to opt in and install). Start rollout.
3. Keep the 12 testers opted in for **14 continuous days**. Ask them to open the app at least a few times.
4. After day 14: Dashboard > **Apply for production** and answer the questions (how testing went, what you changed, readiness). Google reviews, often within about 7 days.
5. When approved: Release > Production > **Create new release** > add the AAB > roll out.

## 4. Fill each form (Dashboard > Set up your app)
| Form | What to enter | Source |
|---|---|---|
| Privacy policy | `https://croplytics.xyz/privacy.html` (check it loads first) | `privacy.html` |
| App access | All functionality available without special access | `data-safety.md` |
| Ads | No ads | `data-safety.md` |
| Content rating | Start questionnaire, email caiden.merklin@gmail.com, category Utility/Productivity, all answers No | `data-safety.md` |
| Target audience and content | 18 and over only; not for children | `data-safety.md` |
| Data safety | Enter the table, encrypted in transit Yes, deletion Yes | `data-safety.md` (decide the declaration row first) |
| Government apps, Financial features, Health | None / No | `data-safety.md` |
| News app, COVID-19 | No | |
| Select app category and contact details | Category Productivity (App). Email caiden.merklin@gmail.com. Website https://croplytics.xyz | `listing.md` |
| Main store listing | Name, short description, full description | `listing.md` |
| Graphics | App icon `icon-512.png`; feature graphic `feature-graphic.png`; phone screenshots `screenshot-1.png` to `screenshot-4.png` | this folder |

## 5. Before you press publish
- Confirm https://croplytics.xyz/privacy.html is live (redeploys about 2 minutes after the push to main).
- Pre-launch report: read it under Testing > Pre-launch report.
- Check Policy status > App content shows no warnings.
- Production > release > Review and roll out. First review can take several days.
