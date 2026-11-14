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
  - `AppEEARS` (the subsetting service we use for most downloads)
- **Check it worked:** log in at https://appeears.earthdatacloud.nasa.gov with the same credentials. Without the approvals above, login succeeds but downloads return 401.

## 2. OpenET API key (highest priority)

- **Sign up:** https://auth.etdata.org (linked from https://openetdata.org as "API"; the older account.etdata.org redirects here)
- **What you get:** an API key shown in the account dashboard.
- **Unblocks:** measured field-level water use, which is our headline validation chart.
- **Note:** the free tier has monthly query quotas. We only query two fields, so the free tier is enough. Record the quota shown on the dashboard.

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

## 6. Anthropic API key (lowest priority, paid)

- **Sign up:** https://platform.claude.com (console.anthropic.com redirects here)
- **What you get:** an API key. Requires billing to be set up.
- **Unblocks:** the AI-written rotation brief. The app falls back to templates without it, so this can wait.

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
