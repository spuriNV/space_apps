# Rotation Factors

What the planner considers when comparing crop rotations. Each rotation (the current one plus 3 alternatives) gets a 0–100 score with a low–high range on every factor. The farmer's sliders set the weights. If two rotations' ranges overlap by more than half, the tool shows them as a tie instead of ranking them.

Full formulas are in `planner-spec.md`, section B4. Data sources reflect the California-first plan; BC is used only for the pitch opener.

## The six priorities named in the brief

| Factor | How it's measured | Data behind it |
|---|---|---|
| **Water use** | Crop water need per month (reference ET × crop coefficient) minus usable rain, giving irrigation need, compared with available water | NASA POWER, GPM IMERG, CIMIS stations; FAO-56 crop coefficients; checked against OpenET measured ET |
| **Forage value** | Forage rating × months harvestable × expected dry-matter yield | Cover-crop and forage factsheets (UC ANR, NRCS) |
| **Nitrogen fixing** | Legumes only: fixing rating × months growing | Factsheets, USDA PLANTS |
| **Erosion reduction** | Bare days × heavy-rain days × slope, compared with the current rotation, blended with the crop's erosion rating | HLS / Sentinel-2 bare-field detection, IMERG, SRTM slope |
| **Organic matter** | Soil-building and residue ratings, years in perennials, days not bare | Factsheets, satellite bare days |
| **Market suitability** | Sell hay vs. feed own herd, equipment, seed cost. Always flagged for local review | Farmer inputs; USDA NASS / AMS prices |

## Extra factors the brief names

| Factor | How it's measured |
|---|---|
| **Pest-cycle break** | Number of different crop families in the rotation, and the longest run of the same family. A rule of thumb; no pest dataset exists |
| **Infiltration / soil structure** | Root depth, compaction-reduction rating, months covered |
| **Nitrogen scavenging** | Catch-crop rating × fall and winter cover months, to stop nitrogen washing out over winter |
| **Supplemental income** | Forage price range minus seed cost, plus cover-crop funding (USDA EQIP practice 340), as a $/ha range |

## Risk and timing (shape the scores; not separate sliders)

- **Exposure:** days when the field is bare *and* there's heavy rain, frost, heat or a dry spell. This is the headline number on the compare screen.
- **How vulnerable the current crop is:** stress weeks found by the AI models from vegetation index, ECOSTRESS land-surface temperature and SMAP soil moisture.
- **Replaying real years:** each rotation run against a drought year (2021–22) and a flood year (2023).
- **Climate scenarios:** "+°C" and "±% rain" sliders recompute water need, frost and heat days, and exposure.
- **Crop-insurance loss history:** the share of past county losses from drought vs. excess moisture (USDA RMA cause of loss).
- **Groundwater:** GRACE storage trend and SGMA basin status.

## Farm constraints (filters, not scores)

- Soil drainage class and water-holding capacity (SSURGO), checked against each crop's tolerance.
- Irrigation water available (surface allocation or groundwater).
- Livestock type.
- Equipment, such as a seed drill.
- "No new perennials."
- Seeding windows, checked against the previous crop's harvest date.

## What it doesn't consider

- Yield or profit modelling.
- Pest or disease data.
- Tile drainage.
- A real soil test.

These are listed as gaps on every rotation brief, along with the items needing review by the farmer and an agricultural adviser.
