# The BC example field, First Nations land and data

This note is for anyone working on the British Columbia example field (`bc_salmon_river_forage`). It explains:
- where the field is relative to reserve land;
- whose territory and water it touches;
- which principles apply to data about First Nations land;
- how we would go about adding a reserve field, if a Nation wanted one.

We are a hackathon team, not a First Nation. Nothing here speaks for any Nation. Where we describe a Nation's interests, we quote or link that Nation's own public pages, or public reporting, and the Nations' own words take precedence over ours.

Links were checked on 15 Nov 2026. Anything we could not open is marked **not verified**.

> Built to be co-developed with First Nations farmers; we'd only add a reserve field with the Nation's permission.

## 1. The example field is not on reserve land

- The field is private, non-reserve farmland in the Salmon Valley, inside City of Salmon Arm limits (Columbia Shuswap Regional District). Its centroid is 50.6434 N, -119.3826 W.
- It is a 21.5 ha forage field: a ParcelMap BC parcel inside the Agricultural Land Reserve, clipped to its AAFC "Pasture / Forages" pixels. The parcel ID and owner are not stored.
- The nearest reserve is **Switsemalph IR No. 3 (Neskonlith), 6.5 km away**. The selection script (`backend/bc/select_field.py`) excluded any candidate within 1 km of a reserve.
- **No reserve land was analysed.** We did not compute crop history, satellite series or any other figure for reserve land, including a count of farmed reserve hectares. The reserve list below comes only from public boundary data.

Being off-reserve does not make the field unconnected. The valley lies within lands that Secwépemc Nations and the Syilx Okanagan Nation speak of as their territory; we have not mapped territories and do not draw that line here. Both have spoken publicly about the Salmon River (section 3). The water this field would draw is the same water the salmon need.

## 2. Nearby Nations and reserves

Source: BC Data Catalogue layer `WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP` (CLSS boundaries with band names), queried 15 Nov 2026. The full list is in `data/cache/bc_salmon_river_forage/reserves_nearby.json`. Distances are straight-line from the field's outline.

| Nation (band name in the layer, number) | Reserves near the valley (distance from the field) |
|---|---|
| **Splatsin** (600) | **Salmon River 1 (Splatsin)**, 1,584 ha (14.2 km); Enderby 2 (17.7 km); Sicamous 3 |
| Neskonlith (690) | Switsemalph IR No. 3 (6.5 km, the nearest); Neskonlith IR No. 2 (26.2 km); Neskonlith 1 (28.0 km) |
| Adams Lake (684) | Switsemalph 7 (7.0 km); Switsemalph 6 (9.0 km); Stequmwhulpa 5; Sahhaltkum 4 |
| Skwlax te Secwépemc (689; "Skwlax te Secwepemculecw" in the layer) | North Bay 5 (14.3 km); Meadow Creek 3; Chum Creek 2; Quaaout 1; Scotch Creek 4 |
| Okanagan Indian Band (Syilx, 616) | Okanagan 1 (17.6 km), which reaches the Salmon River side; Otter Lake 2; Harris 3; Swan Lake 4 |

**Splatsin is the Nation whose reserve sits on the lower Salmon River,** not Neskonlith. Splatsin's own lands page describes IR1 Salmon River as "about 1,600 hectares (4,000 acres) of land along the east side of the Salmon River, approximately 22 kilometres (km) south of Salmon Arm", and says "the land is mostly used for agriculture, grazing and forestry" (https://splatsin.ca/your-government/land, verified).

Reserve land is only part of each Nation's territory. Territories are wider and overlap, and a reserve list says nothing about rights and title. We did not map territories.

## 3. Water and salmon

The Salmon River (written "Swawll Setatkwa" on the PSF page and "akscʷin" on the Okanagan Nation Alliance page, both below) carries Chinook salmon. In drought years the Province has ordered forage irrigators to stop using water so that enough stays in the river for the fish.

| Date | What happened | Source |
|---|---|---|
| 16 Aug 2023 | Fish population protection orders for the lower Salmon River and Bessette Creek. "Approximately 398 surface and groundwater licence holders" had to stop using water for forage crops (grass for hay, alfalfa, forage corn). Livestock watering and domestic use were not covered. | https://news.gov.bc.ca/releases/2023FOR0052-001305 (verified) |
| 2025 | The Secwépemc Fisheries Commission worked with Yucwmenulúcwu (caretakers of the land) staff at Splatsin to assess low-flow barriers to fish passage on the lower Salmon River. Splatsin has a Territorial Water Manager. | https://psf.ca/blog/smarter-drought-monitoring-for-salmon/ (verified with a page fetch; plain `curl` was blocked by the site) |
| 28 Jul 2026 | A temporary protection order was issued for the Salmon River. | BC release below |
| 8 Aug 2026 | The order was rescinded "as farmers and ranchers dealt with elevated wildfire risk in the region" (BC's wording). | BC release below |
| 10 Aug 2026 | The Okanagan Nation Chiefs Executive Council wrote to the Minister, "expressing concerns about the order being rescinded without consultation or a meeting with the Syilx Okanagan Nation". | https://syilx.org/?p=5013 (verified) |
| 19 Aug 2026 | A new temporary protection order: "458 surface water and groundwater licences and transitioning groundwater users in the Salmon River watershed are ordered to stop using water for irrigation of forage crops, lawns, fairways and garden". More than 200 adult Chinook had entered the watershed. | https://news.gov.bc.ca/releases/2026WLRS0042-000965 (verified) |

Note: `docs/handoff-bc.md` said "456 licence holders" for 2026. The release itself says **458 licences** (licences, not holders), so this doc uses 458.

So the planner's question for this field ("what would I grow if irrigation stops in mid-August?") is also a question about the river. The app should present the orders as protecting fish, not as an obstacle to farming.

## 4. Boundary data sources

| Source | What it is | Checked |
|---|---|---|
| NRCan, "Aboriginal Lands of Canada Legislative Boundaries" (Canada Lands Survey System) | The national legislative boundaries of reserves and other Aboriginal lands. https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067 | Title and publisher (Natural Resources Canada) confirmed with a page fetch |
| CLSS map browser | Interactive view of Canada Lands, including reserves. https://clss.nrcan-rncan.gc.ca/mb-nc/en | Opens (HTTP 200) |
| BC Data Catalogue, Indian reserves with band names | BC's copy of the CLSS boundaries with band names. https://catalogue.data.gov.bc.ca/dataset/8efe9193-80d2-4fdf-a18c-d531a94196ad | Opens; the WFS layer `WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP` returned 1,686 features on 15 Nov 2026 |

These are legal survey boundaries of reserves. They are not maps of traditional territory, land use, or where a Nation's rights apply.

## 5. Principles for data about First Nations land

### OCAP®

OCAP® stands for Ownership, Control, Access and Possession. The FNIGC brochure says it "maintains that First Nations have control over data collection processes in their communities" and that "a community or group owns information collectively in the same way that an individual owns his or her personal information". Brochure: https://fnigc.ca/wp-content/uploads/2022/10/OCAP_Brochure_20220927_web.pdf (verified).

OCAP® is a registered trademark of the First Nations Information Governance Centre (FNIGC).

(This attribution wording is from our handoff notes. FNIGC's OCAP training page returned 403 to us, so we could not check the wording against an FNIGC page.)

For this project, OCAP® means satellite or crop data about a reserve field would belong to the Nation. The Nation would decide whether it is collected, how it is used and where it is stored, not us.

### CARE

The CARE Principles for Indigenous Data Governance (Global Indigenous Data Alliance) are **C**ollective benefit, **A**uthority to control, **R**esponsibility and **E**thics. They complement the FAIR data principles. https://www.gida-global.org/careprinciples (verified). The handoff's earlier link, `gida-global.org/care`, now returns 404.

### TCPS 2, Chapter 9

Tri-Council Policy Statement (TCPS 2, 2022), Chapter 9, "Research Involving the First Nations, Inuit and Métis Peoples of Canada": https://ethics.gc.ca/eng/tcps2-eptc2_2022_chapter9-chapitre9.html (verified).

- **Art. 9.1:** when research is likely to affect the welfare of an Indigenous community, "researchers shall seek engagement with the relevant community". The listed conditions include "research conducted on First Nations, Inuit or Métis lands".
- **Art. 9.21:** research that relies only on publicly available information does not require community engagement. The article adds that where information can be identified as coming from a specific community, "seeking culturally informed advice may assist in identifying risks and potential benefits for the source community".

Satellite images and AAFC crop maps of a reserve are public, so Art. 9.21 alone might not require engagement. We do not rely on that. OCAP® and CARE go further than the legal minimum, and a crop map of a named reserve is plainly data about that community's land. We treat any reserve field as needing the Nation's engagement and permission.

We found no FNIGC guidance written specifically for satellite imagery.

## 6. How we would approach adding a reserve field

These steps are a proposal. Each Nation sets its own process, and these steps would give way to it.

1. **Start with Splatsin,** the Nation whose reserve is on the lower Salmon River, through its public lands page: https://splatsin.ca/your-government/land. That page lists the Lands Department and the Territorial Water Manager role.
2. **Send a short, plain-language note.** Say what the tool does and that no reserve data has been analysed. Ask whether there is any interest at all, and accept "no" or no reply.
3. **Ask for the Nation's research protocol and who decides.** A Band Council Resolution or a data-sharing agreement may be needed. Splatsin's land page notes that access to reserve land is approved by Band Council Resolution.
4. **Offer, in writing:**
   - Nation ownership of all outputs for its land;
   - co-design of what is measured and shown;
   - no publication without written consent;
   - data returned or deleted on request;
   - credit, and paid time for anyone who gives it;
   - a version the community controls and hosts, if wanted.
5. **Expect months, not a hackathon weekend.** Nothing is added before the answer is yes.
6. **Talk to the neighbouring Nations and bodies with interests in the river.** Their public contact pages:
   - Neskonlith: https://neskonlith.net/contact-us/
   - Adams Lake (Lands, Natural Resources): https://adamslakeband.org/contact-us/
   - Okanagan Indian Band: https://okib.ca/services/administration
   - Shuswap Nation Tribal Council, Secwépemc Fisheries Commission: https://shuswapnation.org/fisheries/

All of these pages opened on 15 Nov 2026. We list departments only, not people.

Guides to read first:
- Kitasoo/Xai'xais, "Informing Stewardship with Applied Research": https://klemtu.com/wp-content/uploads/2023/05/Informing-Stewardship-with-Applied-Research.pdf (opens)
- Secwépemc research protocol template (Secwépemc Museum, Sept 2018): https://secwepemcmuseum.ca/wp-content/uploads/2024/05/Research_Protocol_September_2018.pdf (opens)

## 7. Agriculture programs for First Nations farmers in BC

Listed as pointers only. Eligibility and intake change, so check the program page.

| Program | Link | Status on 15 Nov 2026 |
|---|---|---|
| BC Indigenous Food Systems and Agriculture hub, including the B.C. Indigenous Pathfinder Service | https://www2.gov.bc.ca/gov/content/industry/agriculture-seafood/indigenous-food-systems-and-agriculture | Verified; the page mentions the Pathfinder Service |
| AAFC Indigenous Pathfinder Service | https://agriculture.canada.ca/en/programs/indigenous-pathfinder-service | Verified |
| Investment Agriculture Foundation (IAF), Indigenous Food Systems & Agriculture Skills & Training Program (ISAT) | https://iafbc.ca/indigenous-food-systems-and-agriculture-skills-and-training-program/ | Page opens. IAF's program list shows ISAT as "Not Accepting Applications". The handoff's IFSAP link (`iafbc.ca/ifsap`) returns 404, and we could not confirm an IAF program called IFSAP. |
| AAFC Indigenous Agriculture and Food Systems Initiative | none found | Our notes say intake is suspended. We could not find a live AAFC program page, so this is **not verified**. |
| Farm Credit Canada, Indigenous financing | https://www.fcc-fac.ca/en/financing/indigenous-financing | Opens (HTTP 200); content not reviewed |

**Not cited:** a "First Nations Agricultural Association (BC)" **could not be confirmed** as a current organisation, so we do not list it. The First Nations Agricultural Lending Association appears only in references from 2003–2006.

## 8. What the app says

The BC field's `why` text in `backend/fields/registry.json` states it is on non-reserve farmland, 6.5 km from the nearest reserve, and links here. Any BC view should also carry the line:

> Built to be co-developed with First Nations farmers; we'd only add a reserve field with the Nation's permission.

## Links we could not verify

- FNIGC OCAP training page (https://fnigc.ca/ocap-training/): HTTP 403. The trademark wording above could not be checked against an FNIGC page.
- AAFC Indigenous Agriculture and Food Systems Initiative: no live page found.
- IAF "IFSAP" (https://iafbc.ca/ifsap): 404.
