# Field Shift: accounts and API keys to obtain

We are building a NASA Space Apps hackathon tool that pulls NASA Earth-observation data and California ground data. The six signups below are needed to unblock the data pipeline. All are free except the LLM key.

**Deliverable:** a filled-in `.env` file (template at the bottom). Do not paste keys into chat, issues, or commits.

**Do them in this order.** 1 and 2 unblock the most.

---

## 1. NASA Earthdata Login (highest priority)

- **Sign up:** https://urs.earthdata.nasa.gov/users/new
- **What you get:** a username and password (not an API key).
- **Unblocks:** SMAP soil moisture, GPM IMERG rainfall, GRACE groundwater, HLS 30 m imagery, MODIS vegetation, ECOSTRESS evapotranspiration.
- **Required extra step:** after confirming the email, log in, go to the profile, then **Applications → Authorized Apps → Approve More Applications**, and approve:
  - `NASA GESDISC DATA ARCHIVE` (IMERG, GRACE)
  - the NSIDC application(s) (SMAP)
  - `LP DAAC Data Pool` (HLS, MODIS, ECOSTRESS)
  - `AppEEARS` (the subsetting service for SMAP, MODIS and ECOSTRESS); also log in once at https://appeears.earthdatacloud.nasa.gov to accept its terms
  - `PO.DAAC Data Website` (OPERA surface-water maps), plus `Earthdata Cloud` if it is offered
  - Exact names may differ slightly; approve the closest match. After setup, `cd backend/nasa && uv run python check_auth.py` reports which approval is missing.
- **Check it worked:** log in at https://appeears.earthdatacloud.nasa.gov with the same credentials. Without the approvals above, login succeeds but downloads return 401.

## 2. OpenET API key (highest priority)

- **Sign up:** https://auth.etdata.org (linked from https://openetdata.org as "API"; the older account.etdata.org redirects here)
- **What you get:** an API key shown in the account dashboard.
- **Unblocks:** measured field-level water use, which is our headline validation chart.
- **Note:** the free tier allows about 100 queries a month (20 a minute) and a 50,000-acre area cap; a 400-query tier needs a linked Google Earth Engine account, which we don't need. A normal run uses 2 queries. Record the quota shown on the dashboard.

## 3. CIMIS AppKey

- **Sign up:** https://cimis.water.ca.gov (Register, confirm email, log in). If registration isn't there, try https://et.water.ca.gov, which hosts the web API.
- **What you get:** an "AppKey" on the account page, used with the web API at `https://et.water.ca.gov/api/data`.
- **Unblocks:** California weather-station reference ET, used to check NASA POWER.

## 4. USDA NASS Quick Stats key

- **Sign up:** https://quickstats.nass.usda.gov/api (request-a-key form)
- **What you get:** a key by email, usually immediately.
- **Unblocks:** county crop acreage, yields and prices.

## 5. USDA AMS My Market News key

- **Sign up:** https://mymarketnews.ams.usda.gov (create an account, then find the API key in the profile). This site timed out from a script on 14 Nov; it may only load in a normal browser.
- **What you get:** an API key for `https://marsapi.ams.usda.gov/services/v1.2/reports`.
- **Unblocks:** California hay prices for the income ranges.

## 6. LLM API key (lowest priority, paid, optional)

- **Use either:** OpenRouter (https://openrouter.ai, one key for many models, prepaid credit) or Anthropic directly (https://platform.claude.com). One is enough.
- **What you get:** an API key. Put a small prepaid amount on it and set a spend limit if the site offers one.
- **Unblocks:** the AI-written wording of the rotation brief. The app falls back to fixed templates without it, so this can wait.
- **Cost stays small by design:** briefs are generated once offline and cached (8 rotations, a few short sentences each), a small model is enough because the text only rephrases numbers we already have, and nothing calls the LLM while someone is using the app.

---

## What to hand back

Create a file named `.env` with exactly these names:

```
EARTHDATA_USERNAME=
EARTHDATA_PASSWORD=
OPENET_API_KEY=
CIMIS_APP_KEY=
NASS_API_KEY=
AMS_API_KEY=
OPENROUTER_API_KEY=   # or ANTHROPIC_API_KEY; one is enough
ANTHROPIC_API_KEY=
```

Also report, for each signup:
- done / not done, and the account email used;
- any quota or rate limit shown;
- anything that differed from these instructions (a moved page, a renamed application, an approval that takes days).

## Not needed (no signup)

NASA POWER, Microsoft Planetary Computer and Earth Search (Sentinel-2, Landsat, CDL), USDA Soil Data Access, CDEC, US Drought Monitor, NOAA NCEI, Google News RSS and GDELT all work without an account.

## Caveat

The sign-up pages above were checked on 14 Nov 2026 and load (except AMS, noted). The Earthdata application names were not checked; if one has been renamed, approve the closest match and note the change.

---

## 7. Render (hosting the live app)

- **Sign up:** https://render.com (sign in with GitHub or email).
- **What it's for:** runs the Field Shift backend and app as one live web service, so the team and judges can use it from a link.
- **Plan:** the free plan works but sleeps when idle (slow first load). Before judging, switch the service to the paid **Starter** plan so it stays awake; check Render's current price.
- **Setup** (after the deploy files are in the repo): New → Blueprint → public Git repository `https://github.com/spuriNV/space_apps` → it reads `render.yaml`. In the service's **Environment** tab, add the keys from `.env` (`EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`, `OPENET_API_KEY`, `CIMIS_APP_KEY`, `NASS_API_KEY`, `AMS_API_KEY`). Never paste them anywhere else.
- **Hand back:** the service URL (ours: `https://croplytics-app.onrender.com`) and which plan it's on.
