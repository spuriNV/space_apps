# NASA Space Apps Winner Inspiration Handoff (for CropLytics, Field Shift 2026)

## Start here
This handoff collects the 50 NASA Space Apps Global Winners from 2021 to 2025, every winner demo that can still be watched or read, the official 2026 judging rules, and the seven Field Shift 2026 videos other teams have already posted. The aim is to show what wins and turn it into a 30-second video and a 7-slide deck for CropLytics. The 2026 winners are not out yet: Global Nominees are due 3 Dec 2026, Finalists 17 Dec 2026 and Winners 26 Jan 2027.[^1]

- [2026 Judging & Awards Guide](https://www.spaceappschallenge.org/resources/judging-awards-guide/): five criteria scored 1-5, and the ten awards.
- [Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/): demo limits and the official 30-second timeline.
- [Field Shift challenge video (NASA, 3:37)](https://www.youtube.com/watch?v=cF0U2WXsM7o): the challenge author and the subject-matter experts. Transcript: `transcripts/2026_NASA_FieldShift_ChallengeVideo.txt`.
- Winner lists: [2025](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/) · [2024](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-international-space-apps-challenge-announces-2024-global-winners/) · [2023](https://science.nasa.gov/directorates/smd/2023-nasa-international-space-apps-challenge-announces-10-global-winners) · [2022](https://legacy.spaceappschallenge.org/blog/2022-global-winners/) · [2021](https://legacy.spaceappschallenge.org/blog/meet-the-2021-global-winners/)
- The closest precedent, the 2024 Best Use of Data winner: [WaterWise demo (31 s)](https://www.youtube.com/watch?v=Wg-gE3kYaas), in `videos/2024_GaamaRamma_WaterWise.mp4`.

**The findings in brief**
1. **Hard limits.** The demo must be a video of 30 seconds or less, or a deck of no more than 7 slides including the title. Anything over either limit is ineligible for global judging. A video in another language must carry English subtitles.[^2]
2. **Five criteria, all scored 1-5.** They are Impact, Creativity, Validity, Relevance (NASA data used as a core part of the solution) and **Presentation**. Presentation is new as a scored criterion. Judges score it from the demo *and* the full project page, and "the majority of judges' evaluation will be based on your project submission."[^1][^2]
3. **Farm-water tools win.** The 2024 agriculture challenge produced 2 of that year's 10 Global Winners. WaterWise (Best Use of Data) gives a 7-day irrigation schedule from OpenET. 2plant (Galactic Impact) tells a farmer when a field is too wet to plant, using SMAP and OpenET. Each turned **one decision** into an app built on one or two NASA datasets.[^3][^4]
4. **Winning videos are plain, short and mostly product.** Of the 15 verified winner demos, 13 run 28-31 s, and most are screen recordings with a voice-over or burned-in captions. No winner used polished cinematics; the Best Use of Data video even shows the browser's other tabs.
5. **The Field Shift field is crowded and generic.** All seven public 2026 Field Shift videos open on a nameless "farmer at the edge of a field", list POWER, SMAP, MODIS and GPM, and run 67-244 s. **None of them shows a validation result.** CropLytics' real fields, measured-water check and BC story set it apart.
6. **The Field Shift experts work on ISS astronaut photography.** Two of the four NASA JSC people in the challenge video work on astronaut photos of Earth (Dr William Stefanov, Alex Stoken). CropLytics already uses an ISS photo of the Sacramento Valley, so put it up front and credit it.[^5]

## Rules that decide eligibility and score (2026)
| Item | Rule | Source |
|---|---|---|
| Demo format | A video of 30 s or less, **or** a deck of 7 slides or fewer, including the title and intro slides. Over the limit means ineligible for global judging. | [^2] |
| Language | English. A video may be spoken in another language but must have English subtitles. | [^2] |
| Hosting | A public link that needs no login (YouTube, Drive, GitHub and so on). Uploading to the Space Apps site isn't possible. | [^2] |
| Slide content | Team name, **team member names** and the challenge. Show an image of the project, the user experience, and how NASA or partner data makes the solution possible. | [^2] |
| Official video timeline | 0:00 who you are · 0:02 the challenge and why you chose it · 0:05 the project title and tagline · 0:10 how it works, the user experience and the NASA data · 0:20-0:30 the future: "what can your solution do for people, the world". | [^2] |
| AI ("Super Intelligence") use | Allowed. AI-generated images and video **must carry a visible watermark**, and AI audio, code and data must be acknowledged in text and metadata. Generated content may not use NASA logos or branding. AI must not be used to come up with the idea. | [^2] |
| NASA data | At least one NASA dataset or resource is required for a Global Award. Data from the Space Agency Partners is encouraged; **CSA and ESA are 2026 partners**, so Sentinel-2 counts as partner data and is worth naming. | [^2] |
| People under 18 | No images, video, audio or likeness of anyone under 18. | [^2] |
| Ten Global Awards | Best Use of Science · Best Use of Data · Best Use of Technology · Galactic Impact · Best Mission Concept · Most Inspirational · Best Storytelling · Global Connection · Art & Technology · Local Impact | [^1] |

**Judging criteria (verbatim headings, paraphrased "5" level):**
- **Impact:** a significant problem, wide reach, inspires or benefits a large audience.
- **Creativity:** new, or a meaningful improvement on existing ideas; challenges conventional methods.
- **Validity:** scientifically sound, technically feasible, ready for real use, *usable and user-friendly*.
- **Relevance:** fully addresses the challenge; NASA data is *integral*, not a superficial addition.
- **Presentation:** a clear, engaging and well-structured story of the challenge, the solution and why it matters, judged from the demo and the full project.[^1]

The team's `docs/judging-rubric.md` quotes the first four criteria accurately. Add **Presentation** as a fifth, scored criterion.

## Priority projects (agriculture, water, climate and Earth observation)
| Year | Award | Project | What to take from it | Best public links |
|---:|---|---|---|---|
| 2024 | Best Use of Data | **WaterWise** (GaamaRamma) | One decision (when and how much to irrigate) from one NASA-linked dataset (OpenET). A raw 31 s screen recording with burned-in captions: name and promise, add a field, a 7-day schedule, an AI helper, a tagline. | [Demo](https://www.youtube.com/watch?v=Wg-gE3kYaas) · [App](https://nasa-hackathon-2024-nine.vercel.app/) · [Team](https://www.spaceappschallenge.org/nasa-space-apps-2024/find-a-team/gaamaramma/) |
| 2024 | Galactic Impact | **2plant / ! 2plant** (NVS-knot = Nave Analytics + VITech) | A human origin story: a co-founder's farmer father asked, "can you tell me where it's still too wet... where I'm going to get the tractor stuck?" Uses SMAP soil moisture and OpenET; NASA, ESA and JAXA imagery; the team "made complex data simple and actionable." | [Story](https://siliconprairienews.com/2025/02/nebraska-startup-wins-nasas-galactic-impact-award-in-the-2024-space-apps-challenge/) · their pitch in `transcripts/official_2024_GlobalWinnersAnnouncement.txt` · [Team](https://www.spaceappschallenge.org/nasa-space-apps-2024/find-a-team/nvs-knot/) |
| 2025 | Local Impact | **QUEÑARIS** (Peru) | A 30 s video in title cards, one per beat: Problem with a number ("springs drop from 14 litres a second to zero in days") → Solution → NASA satellite data + drones + AI → **traction** ("5,000 seedlings ready and local support") → team names. A community water story. | [Demo](https://www.youtube.com/watch?v=1PAig22pWuQ) · `frames/2025_QUENARIS/` |
| 2025 | Art & Technology | **Henry's Farm Adventure** (Zumorroda-X) | Won on the agriculture challenge ("NASA Farm Navigators") with a game about a farmer adapting to heat and flood. Craft and story count. | [Team](https://www.spaceappschallenge.org/2025/find-a-team/zumorroda-x/) |
| 2025 | Best Use of Technology | **SkySense** (Twisters) | Turned NASA Earth observation and weather data into one plain question, "Will it rain on my parade?", answered as probabilities and the safest time window. | [Team](https://www.spaceappschallenge.org/2025/find-a-team/twisters/) |
| 2023 | Best Storytelling | **Aqua Explorer** (Team Voyagers) | Water-cycle game. The 30 s cut is team card → challenge → game → NASA/GISS chart → call to action; the 240 s local cut opens on a named child, "Maya, a girl from a small village". | [30 s](https://www.youtube.com/watch?v=mtHMyOQ0vzA) · [240 s](https://www.youtube.com/watch?v=2ydwoGXQ80Y) |
| 2023 | Galactic Impact | **Greetings from Earth!!** (Ocean Gardens) | A framing device ("a radio transmission to TRAPPIST-1") plus a NASA chlorophyll map and a game; music only, with text on screen. | [Walkthrough](https://www.youtube.com/watch?v=kBpo6U7iJnU) |
| 2021 | Local Impact | **Landslide Detection Squad** | Opens on a sourced impact number ("4.8 million people affected, 18,000 deaths", BBC), then the mechanism, then a live map, then an evacuation output. | [Demo](https://youtu.be/gvxFAl7jtqc) |
| 2021 | Most Inspirational | **SIMACT** (Bioshi, Panama) | A deforestation monitor built for Indigenous communities in the Darién "whose voices are silenced". This is the closest precedent for a First Nations angle. (The demo link is dead.) | [Project](https://2021.spaceappschallenge.org/challenges/statements/space-for-change/teams/bioshi/project/) |
| 2021 | Best Use of Science | **de Bugger** (Ani's Cuff) | Earth-observation layers into a U-Net species map. Later partnered with a Taiwan government institute, which shows what "impact beyond the hackathon" looks like. | [Demo](https://www.youtube.com/watch?v=gePuvUXV4iU) · [Interview](https://www.youtube.com/watch?v=AkDtOF3bpOY) |
| 2021 | Best Use of Technology | **SHINE** (Change Maker) | A mobile app on the **NASA POWER API** for homeowners: a precedent for POWER as a core dataset. (The video is gone.) | [Project](https://2021.spaceappschallenge.org/challenges/statements/you-are-my-sunshine/teams/change-maker/project/) |
| 2022 | Best Use of Data | **Starflock** | NASA FIREX-AQ airborne data: wildfire smoke versus agricultural-burn smoke. (The deck has been deleted.) | [Project](https://2022.spaceappschallenge.org/challenges/2022-challenges/take-flight/teams/starflock-3/project/) |

**Inspiration:** both agriculture winners solved *one farmer question*, used the NASA dataset as the engine of the answer, and showed the app producing it in under 30 s. CropLytics has more data than either. The risk is dataset soup, not too little data.

## All Global Winners, 2021-2025
Full detail (challenge, country, datasets, demo status, structure, on-screen notes) is in `winners.csv`. "Video" means a demo video is in `videos/`; "dead" means the link no longer works; "—" means no public demo was found.

| Year | Award | Team · Project | One-line idea | Demo |
|---:|---|---|---|---|
| 2025 | Science | SpaceGenes+ | Dashboard of combined radiation and microgravity gene effects | — |
| 2025 | Data | Resonant Exoplanets | AI scans JWST and other spectra for exoplanets and biosignatures | — |
| 2025 | Technology | Twisters · SkySense | NASA Earth observation turned into hyperlocal rain and heat odds and safe time windows | — |
| 2025 | Galactic Impact | Astro Sweepers | A "credit score" for satellites from debris data | — |
| 2025 | Mission Concept | PureFlow | Design a 3D habitat, then test it against solar storms | dead (29 s) |
| 2025 | Inspirational | Photonics Odyssey | Sovereign LEO internet for India's 700M without broadband | — |
| 2025 | Storytelling | HerCode Space · A Solar Tale | Illustrated space-weather story for children | — |
| 2025 | Global Connection | Gaia+LEO | Optimisation that moves AI compute to orbit to save Earth's water and power | — |
| 2025 | Art & Tech | Zumorroda-X · Henry's Farm Adventure | Farmer adaptation game from NASA data | — |
| 2025 | Local Impact | QUEÑARIS | Queñua reforestation for Arequipa's water | video 30 s |
| 2024 | Science | WMPGang · SkyShield | Orrery showing satellite risk zones from NEO and meteor data | — |
| 2024 | Data | GaamaRamma · WaterWise | 7-day irrigation schedule from OpenET | video 31 s |
| 2024 | Technology | 42 QuakeHeroes | Deep neural network to detect seismic events | dead |
| 2024 | Galactic Impact | NVS-knot · 2plant | Planting window and too-wet or frost risk from SMAP and OpenET | — (pitch in announcement) |
| 2024 | Mission Concept | AsturExplorers · Landsat Connect | Landsat pass alerts and surface reflectance | dead (31 s) |
| 2024 | Inspirational | Innovisionaries · Eco-Metropolis | City-building game on real environmental data | announcement clip |
| 2024 | Storytelling | TerraTales | Climate stories from Egypt, Brazil and Germany, plus an AI forecast | — |
| 2024 | Global Connection | Asteroid Destroyer | 3D map of exoplanets HWO could characterise | video 45 s (probable) |
| 2024 | Art & Tech | Connected Earth Museum | Virtual climate museum with an AI host | video 30 s |
| 2024 | Local Impact | Team I.O. · G.R.O.W. | Wildfire GIS in plain language | video 218 s |
| 2023 | Science | LunarTech Ensemble | Apollo moonquake site and game | — |
| 2023 | Data | Storm Prophet | 40 h LSTM forecast from DSCOVR data, with RSS alerts | video 41 s |
| 2023 | Technology | Spacebee | Moonquake Map 2.0 | dead (31 s) |
| 2023 | Galactic Impact | Greetings from Earth!! | Oceans as "gardens": NASA ocean data | walkthrough 114 s |
| 2023 | Mission Concept | ASTROGENESIS | Planetary tourism itineraries | — |
| 2023 | Inspirational | Space Quest Maidens | Eclipse teaching tool for children | fundraiser clip |
| 2023 | Storytelling | Team Voyagers · Aqua Explorer | Water-cycle game | video 30 s |
| 2023 | Global Connection | Arcobaleno | Sonified NASA images for blind users | — |
| 2023 | Art & Tech | Oogway Comics | Exoplanet comic from NASA data | — |
| 2023 | Local Impact | $quality_over_quantity | Imaging spectroscopy of a biodiversity hotspot | — |
| 2022 | Science | What's New? | Three-stage ML solar-storm pipeline | **deck, 7 slides** |
| 2022 | Data | Starflock | FIREX-AQ smoke chemistry | deck deleted |
| 2022 | Technology | tAMing particles | 3D-printed Mars habitat kit | Canva deck |
| 2022 | Galactic Impact | Selene | 3D moonquake visualiser | video 30 s |
| 2022 | Mission Concept | Mars 3D Home | Mars habitat interior | dead |
| 2022 | Inspirational | Team Diamonds | Variable-star game for children | video 28 s |
| 2022 | Storytelling | MIMBI | QR-code story of Paraguay's first satellite, run in local shops | video 30 s |
| 2022 | Global Connection | Standard NCTU CS Student | 3D ISS tracker | video 31 s |
| 2022 | Art & Tech | Earth, Wind & Flare | LED space-weather panel | **deck, 7 slides** |
| 2022 | Local Impact | Brute Force | Apollo seismic station map | video 30 s |
| 2021 | Science | Ani's Cuff · de Bugger | Insect distribution from Earth observation plus a U-Net | video 30 s |
| 2021 | Inspirational | Bioshi · SIMACT | Deforestation monitor with Indigenous communities | dead |
| 2021 | Data | Cambridge Asteroids | Asteroid light-curve generator | dead (Vimeo) |
| 2021 | Technology | Change Maker · SHINE | NASA POWER solar app | dead |
| 2021 | Global Connection | Eagle AI | Ocean plastic from Landsat and Sentinel-2 | dead |
| 2021 | Art & Tech | Jimmy in the Box | Raspberry Pi origami JWST | **deck, 7 slides** |
| 2021 | Mission Concept | Mohakash | Regolith sampler (RASSOR-inspired) | video 28 s |
| 2021 | Local Impact | Landslide Detection Squad | Canopy tilt as a landslide precursor | video 31 s |
| 2021 | Storytelling | Space Travelers | Mars-hazards game | dead |
| 2021 | Galactic Impact | 4 Seeds · Infinipod | Aeroponic crop pods for space | video 30 s |

Eighteen of the 50 winners are Earth, agriculture, water or climate projects; the rest are space science, habitats and education.

## Field Shift 2026: what the challenge and its experts want
The NASA challenge video speaks the brief almost word for word: *"Compare rotations, reveal trade-offs, understand risk, make uncertainty visible. Build an AI model, an interactive map, a visualization, a decision support tool..."* It names "rainfall, soil moisture, heat, vegetation, water: different observations, different scales, pieces of the same story."[^5]
- The challenge author is Sadie Barnett-Boudreau of NASA JSC.
- The subject-matter experts are Dr William Stefanov (senior Earth systems scientist; ISS imagery for disaster response and remote sensing), Alex Stoken (data scientist; machine learning on **astronaut photography of Earth**) and Anudeep Gogineni (data solutions architect).
- **Use the challenge's own verbs** ("compare rotations", "trade-offs", "make uncertainty visible") as section labels in the deck and on screen. Judges map them to Relevance straight away.
- CropLytics' phrase "different observations, different scales" is exactly its 3D stack: surface, then soil moisture, then groundwater, each drawn at its real pixel size. That is the strongest single shot for Relevance and Creativity.

## The competition already public (Field Shift 2026)
Seven other teams' Field Shift videos are on YouTube, mostly the longer local-event cuts. They are downloaded, transcribed and OCR'd under `videos/fieldshift2026_*`.

| Team · project | Length | Opening line | NASA data named | Validation shown |
|---|---:|---|---|---|
| Astro Stack · FarmStack (Bangladesh) | 244 s | "A farmer stands at the edge of an empty field..." | GPM, MODIS, POWER, SMAP | none |
| FIELD-IQ | 238 s | "A farm is never just a piece of land..." | GPM, MODIS, POWER, SMAP | none ("does not try to predict every uncertainty") |
| ThunderBoltC · RotaShift (Bangladesh) | 236 s | "When does the season start? Ask a farmer..." | IMERG | none; lists ground truth as future work |
| Team Groot · Sky2Root: "test your next crop rotation on 40 years of NASA data" | 190 s | "A farmer gets about 40 seasons in a lifetime..." | GPM, Landsat, POWER, Sentinel, SMAP | none (cites one global maize statistic) |
| fasa · Yield Shift | 93 s | "Every single second, climate change..." | POWER | none |
| Team Jericho · Vinland (Cairo) | 68 s | "Hi everyone, we are team Jericho..." | POWER, SMAP, MODIS, ECOSTRESS | none |
| SpaceSoil | 67 s | "Every farmer starts with a plan..." | none named | none |

**Where CropLytics is different:** real, named fields with real acreage and real events (Colusa 2022 fallowing, BC's 2023 irrigation order); one measured-water check (+16% and +21% against OpenET, nothing tuned); NASA data checked against NOAA stations; BC and First Nations co-development; mobile apps. Sky2Root is the nearest on rotations: its "40 seasons" hook is strong, so don't reuse that phrasing.

## What winning videos have in common
Based on the 15 verified 2021-2025 winner demo videos, with transcripts in `transcripts/` and OCR'd frames in `frames/<name>/ocr.txt`.

1. **Length.** 13 of 15 run 28-31 s; the median is 30 s. Two older winners ran 41 s and 45 s. Under the 2026 rules those would be ineligible, so aim for 28-29 s.
2. **The first three seconds.** Openings split three ways:
   - The product name and promise: WaterWise ("WaterWise, for better farm water management"); de Bugger ("to combat the loss of insect biodiversity...").
   - A sourced impact number: Landslide ("4.8 million affected, 18,000 deaths", with BBC on the card); QUEÑARIS (springs falling from 14 L/s to zero).
   - The team and challenge: Team Diamonds, Team Voyagers, Mohakash, Storm Prophet.

   Nobody spends more than about 3 s on the team.
3. **Demo against slides.** About 10 of 15 are mostly live product (screen recordings, often with the URL bar visible). Three are title-card-led (QUEÑARIS, 4 Seeds, Team Voyagers), and even those show the product by about 0:10. A working thing on screen is the norm.
4. **How NASA data appears.** It is named *in the narration or as a source line on the chart*, not as a logo wall:
   - WaterWise says "OpenET".
   - Team Voyagers shows a chart labelled "Data source: NASA/GISS".
   - Team Diamonds shows a "NASA/Aarhus/T. White, K2 Mission" credit.
   - Landslide shows its "Landslide susceptibility map" layer.

   Most winners show one or two datasets, not five or more.
5. **A human or community story.** It is present in the strongest Impact and Inspiration winners: QUEÑARIS (a city's water), MIMBI ("300 people in 4 hours" in local shops), Bioshi (Indigenous communities), 2plant (a farmer father), and Team Voyagers' longer cut ("Maya").
6. **Impact numbers.** About half state one number: people affected, litres a second, seedlings ready, people reached. It is a single number, not a dashboard of them.
7. **Captions.** Most winners burn in captions or put key words on screen (WaterWise, Selene, the ISS tracker, QUEÑARIS cards). Judges often watch on mute.
8. **Production.** Plain. Raw screen recording, a laptop voice-over and stock music. Clarity beats polish; no winner used cinematic B-roll or AI imagery.
9. **The ending.** A tagline or a future line: "WaterWise: get your farm's water usage right"; "...into next-generation scientists"; QUEÑARIS ends on traction (5,000 seedlings) and then team names; Landslide ends on the operational output (evacuation centres).

## What winning decks have in common
Three winner decks could be extracted (`slides/*.pdf`, text in `slides/*.txt`, thumbnails in `frames/slides_*`).
- **All three are exactly 7 slides**, using the whole allowance. Each has 394-681 words in total, about 55-100 words a slide.
- **Slide 1** carries the challenge name, project name, a one-line motto or tagline, the location and the repository link. What's New? also lists every team member.
- **The arc** is: problem and why it matters (with a dated, sourced number: "9M people affected for 9 days in Quebec, '89") → objective → how it works (a diagram) → results (plots) → future or awareness plan.
- **Credits on the slide.** NASA image credits ("Credits: NASA/Walt Feimer"), source URLs under figures, and honest limits. Jimmy in the Box says outright that it used no NASA science data, and still won Art & Technology.

## Recurring themes across winners
- **Turn hard science into one plain question** ("Will it rain on my parade?", "to plant or not to plant", "when do I irrigate?").
- **Education and games for children.** This is the largest single cluster (Team Diamonds, Space Travelers, Team Voyagers, Space Quest Maidens, Eco-Metropolis, HerCode, Zumorroda-X).
- **Local problem, global data.** Local Impact winners are all about a named place (Arequipa, Perth slopes, Florianópolis, Taiwan's hotspot, Nicosia).
- **Real-world traction or a pilot** shows up in Impact-heavy wins: QUEÑARIS's seedlings, MIMBI's 300 people, 2plant's beta with irrigation customers, de Bugger's government partnership.
- **Multi-agency data** (NASA plus ESA, JAXA or CSA) appears in Earth-observation winners: Eagle AI (Landsat and Sentinel-2), 2plant (NASA, ESA and JAXA).

## Common mistakes in non-winners (visible in the downloaded comparison videos)
- **Too long.** Agrosour (2024, 137 s) and every 2026 Field Shift local cut except SpaceSoil and Vinland run well past 30 s. These may be local-event cuts, but submitted as the global demo they would be disqualified.
- **No NASA data on screen.** Agrosour's silent app tour starts at a Google sign-in screen and shows "Hello world" test posts and IoT sensor numbers, but no NASA dataset. AgriAstra (31 s) says only "open Earth observation data".
- **A generic farmer opener.** Six of seven 2026 Field Shift videos open on an unnamed farmer and a cliché. There is no place, no date and no number.
- **A dataset list with no proof.** The videos name four or five datasets but show no check against the ground and no uncertainty, which is exactly what the brief asks for ("make uncertainty visible").
- **Team introductions that run 15-20 s** (FarmStack, Team Voyagers' 240 s cut). This is fine at a local event but fatal in 30 s.

## Recommendations for CropLytics
These build on `docs/pitch.md` (the current 7-slide plan and 30 s video) and `docs/judging-rubric.md`. Read them as edits to that plan, not a replacement.

**Positioning**
- **Award targets, in order:**
  1. **Best Use of Data**: WaterWise is the precedent, satellite water for farm decisions.
  2. **Local Impact**: BC's Salmon River and the First Nations co-development.
  3. **Galactic Impact**: 2plant is the precedent.

  The validation story (a held-out check against OpenET and stations) is also the best evidence for **Best Use of Science** ("the most valid use of the scientific method").
- **One sentence, in the challenge's own words:** "CropLytics compares rotations for a real field, reveals the trade-offs in water, soil and bare days, and makes the uncertainty visible, checked against the ground." Put it on slide 1 and in the video's first 5 s.
- **One decision on screen.** Show the dry-year switch (rice to safflower: about 2 against about 5 acre-ft/acre). Show everything else only in the deck.
- **Lead NASA data with the ISS photo and the 3D stack.** The ISS astronaut photo opens the piece, credited to NASA JSC Earth Science and Remote Sensing; that is exactly what the experts work on. The 3D stack (surface, then SMAP root zone, then GRACE-FO groundwater, each at its real pixel size) is "different observations, different scales" made visible.
- **Name 3 NASA datasets on screen in the video, and all of them in the deck.** In the video use HLS (Landsat + Sentinel-2), SMAP and GRACE-FO, with POWER or IMERG in a source line. In the deck name the rest: MODIS, ECOSTRESS, IMERG, POWER, NASADEM, OPERA DSWx and ISS. Also name **ESA Sentinel-2** and, if any CSA data is used for BC, CSA, since both are 2026 partner agencies.
- **One validation number, said plainly:** "Our water estimate runs 16-21% above OpenET's satellite measurements; we tuned nothing." No competitor shows any check, so this is the edge on Validity.
- **Treat the First Nations angle as the Most Inspirational and Local Impact story, and keep it accurate.** Bioshi (2021 Most Inspirational) won on building *with* Indigenous communities. Name the Nation and quote or show a partner only with their explicit permission. If co-development is planned rather than done, say "being co-developed with" or "next: co-design with". Note that `pitch.md` doesn't mention it yet.
- **Show the phone.** Spend 1-2 s on the iOS or Android app with a field card in a hand or on a device frame. It makes "farmer-first" and usability concrete.
- **No AI imagery.** Use real screenshots, the ISS photo and screen recordings. If any AI image or voice is used, it needs a visible watermark under the 2026 rules, and no NASA logos in generated content.

### 30-second video outline
Format 1920×1080, burned-in English captions, about 70 spoken words, target **28-29 s**. Every shot has a source line naming the dataset. The structure follows the official timeline but compresses the team intro into a lower-third, as most winners do.

| Time | Picture | Voice-over (about 70 words) | On-screen text / source line |
|---|---|---|---|
| 0:00-0:04 | ISS astronaut photo of the Sacramento Valley, slow push-in; lower-third with the team and challenge names | "August 2023: BC ordered about 398 licence holders on the Salmon River to stop irrigating, mid-season." | CropLytics · Field Shift · NASA Space Apps 2026 / *ISS astronaut photo, NASA JSC* |
| 0:04-0:08 | App on the phone and web, field card "Rice field, Colusa County, 149 acres" | "CropLytics helps a grower choose next season's rotation, with NASA data, on their own field." | Compare rotations · reveal trade-offs · see the risk |
| 0:08-0:13 | "This field's year" strips, cursor on 2022 (brown all year) | "NASA's Landsat and Sentinel-2 imagery shows this field: fallowed in the 2022 drought." | 2022: no rice planted / *NASA HLS (Landsat + Sentinel-2)* |
| 0:13-0:18 | The 3D stack: surface, then soil moisture, then groundwater under the field | "Below it: soil moisture and groundwater, from SMAP and GRACE, at their true scale." | Different satellites, different scales / *SMAP L4 · GRACE-FO* |
| 0:18-0:23 | Compare view, "Dry-year safflower" card, "You gain / You give up" | "Switch to safflower in a dry year: about 2 acre-feet of water instead of 5. Less ground cover." | ~2 vs ~5 acre-ft/acre · more bare days |
| 0:23-0:26 | The validation bar against OpenET | "Checked against measured water use: our model runs 16 to 21 percent high. We tuned nothing." | Checked, not tuned: +16-21% vs OpenET |
| 0:26-0:29 | Salmon River field in BC on the map; end card | "Next: home to BC, co-developed with [the Nation, by name and with permission]." | Built in California · checked there · next stop BC |

Notes:
- If the First Nations wording can't be confirmed before submission, end with "Next stop: BC" alone.
- Keep the music low, since the captions carry the message on mute.
- Check the exported file's length with `ffprobe` and keep it at 29.5 s or less.

### 7-slide outline
Use all seven slides, like the winners. Keep each to about 60 words or fewer, with one big visual and a source line under every figure. This revises `pitch.md` section 2; the changes are in **bold**.

1. **Title.** CropLytics: plan next season's rotation with NASA Earth data. **Add the team name and every member's name (required)** and the challenge "Field Shift: Adapting Farms with NASA Data". Show the ISS photo with its credit, the web and app links, and the one-sentence pitch written in the challenge's words.
2. **The problem, a real place and a date.** BC, 16 Aug 2023: about 398 licence holders were told to stop irrigating. Sumas Prairie flooded in Nov 2021. **Add one sentence on the First Nations co-development, with permission.** Then the data gap: no field-scale water measurement in BC.
3. **Built where it can be checked.** Fourteen California fields (not two, if the 14-field build is live; reconcile this with `pitch.md`) plus the Salmon River field in BC. Show a map screenshot.
4. **What the grower sees: the user experience.** "This field's year", "Coming season", and the phone screens side by side, all in inches, acre-feet and days.
5. **NASA data at the core.** The 3D stack image, with a table of each dataset → what it answers → its resolution: HLS, SMAP, GRACE-FO, MODIS, ECOSTRESS, IMERG, POWER, OPERA DSWx, NASADEM, ISS, plus **ESA Sentinel-2 as partner data**. **Update the "not in yet" line in `pitch.md` to match `judging-rubric.md`**, which says SMAP, MODIS and ECOSTRESS are now live.
6. **Compare, and how we know it's right.** Safflower against rice in acre-feet, gains and give-ups with ranges, then three small charts: OpenET +16% and +21%; POWER and IMERG against NOAA stations; rule against machine learning on unseen fields. **Label the uncertainty plainly; it is the brief's own ask.**
7. **Impact and the next step.** **One sourced reach number** (for example California rice or Kings County alfalfa acres from USDA NASS; the rubric flags this as a gap), the honest limits, and the next step: a BC field with a measured water check, co-developed with the Nation. Close on the tagline.

### Other changes to make before submission
- **Fill in the project page.** Most of the score comes from the project page, not the demo. Fill in "NASA Data" dataset by dataset (product names, versions, links), list ESA Sentinel-2 under partner data, and fill in the SI-use disclosure.
- **Make every link public with no login.** Request FortiGuard web-filter classification for the web app's domain, as the submission guide recommends.
- **Don't show people under 18** in any footage or photo.
- **Rehearse Presentation as a criterion.** Run a cold-viewer test: someone with no context watches the 30 s on mute and says back the problem, the product and the NASA data. If they can't, cut words.

## Fast browsing order
For maximum inspiration per minute:
1. Watch WaterWise (31 s), then QUEÑARIS (30 s), then Landslide Detection Squad (31 s). Those three are the template.
2. Read NVS-knot's 2plant pitch in `transcripts/official_2024_GlobalWinnersAnnouncement.txt` (search "andv snot") for the farmer-dad story.
3. Watch the Field Shift challenge video at 0:00-1:45 for the brief's own words.
4. Skim two competitors, Sky2Root and RotaShift, to know what judges will see next to CropLytics.
5. Open `slides/2022_WhatsNew.pdf` and `slides/2022_EarthWindFlare.pdf` for 7-slide pacing.

## Method, files and gaps
- **Lists:** official NASA and Space Apps winner announcements for each year (see `sources.md`). The 2021 and 2022 project pages are public and gave summaries, demo links and datasets. For 2023-2025, the project tab on spaceappschallenge.org needs a login. Team pages show only the team, challenge and badges, so those demo videos were found by public YouTube search (`scripts/yt_queries_round*.txt`, raw hits in `scripts/yt_results_round*.tsv`). A hit counted as a match only when the channel name matched a listed team member or the title named the team and project. "Probable" is marked in `winners.csv`.
- **Downloads:** `scripts/dl.sh` (yt-dlp, 720p or lower, YouTube captions where available) put 34 videos in `videos/` with `.info.json` metadata. `scripts/process.py` produced:
  - transcripts in `transcripts/` (txt, srt, vtt, tsv, json; YouTube captions first, faster-whisper base on CPU otherwise);
  - one frame every 3-10 s, deduplicated by perceptual hash and OCR'd with RapidOCR, in `frames/<name>/` (`ocr.txt` holds timestamped text).

  Decks were exported from public Google Slides to `slides/`.
- **Gaps:**
  - The 40-per-year **Global Finalists** lists load client-side from the site's API and weren't collected, so finalist coverage is limited to the winners. Non-winners are shown through agriculture Global Nominees and comparison videos instead.
  - 11 winner demo links are dead (terminated accounts, private videos, Vimeo login, Drive 404), and 16 winners have no public demo found.
  - The "TerraTales" 30 s video found is from 2025 and is not the 2024 winner's demo. The 2024 Asteroid Destroyer video is a probable, not confirmed, match.
  - 2026 winners: not announced (expected 26 Jan 2027).
- **Reproduce:** `scripts/make_csv.py` rebuilds `winners.csv`. Rerun the downloads and processing with `scripts/dl.sh scripts/list2.txt`, then `uv run --no-project --with rapidocr-onnxruntime --with faster-whisper --with pillow --with imagehash python -I scripts/process.py`.

---

## References

[^1]: [Judging & Awards Guide (2026)](https://www.spaceappschallenge.org/resources/judging-awards-guide/): the criteria, the ten Global Awards, and the 2026 dates (nominees 3 Dec, finalists 17 Dec, winners 26 Jan 2027).
[^2]: [Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/): "Tips for Creating a Project Demo", the 30 s timeline, the 7-slide content rules, SI watermark rules, the 2026 Space Agency Partners, the under-18 rule, and "the majority of judges' evaluation will be based on your project submission".
[^3]: [NASA: 2024 Global Winners](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-international-space-apps-challenge-announces-2024-global-winners/); [Universe Magazine on NVS-knot (SMAP, OpenET)](https://universemagazine.com/en/ukrainian-team-wins-nasa-space-apps-challenge-2024).
[^4]: [Silicon Prairie News: Nave Analytics and VITech win Galactic Impact](https://siliconprairienews.com/2025/02/nebraska-startup-wins-nasas-galactic-impact-award-in-the-2024-space-apps-challenge/); [2024 Global Winners Announcement video](https://www.youtube.com/watch?v=DcDuDq9wGzg).
[^5]: [NASA Space Apps: "2026 Challenge | Field Shift: Adapting Farms with NASA Data"](https://www.youtube.com/watch?v=cF0U2WXsM7o), uploaded 29 Oct 2026; transcript and OCR'd name cards in `transcripts/` and `frames/2026_NASA_FieldShift_ChallengeVideo/`.
