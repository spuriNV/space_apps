"""Windows, queries and place terms, copied from planner-spec.md B9."""
WINDOWS = {
    "car_2022_drought": dict(
        preset="car_colusa_rice", start="2022-02-01", end="2022-11-30", hl="en-US", gl="US", ceid="US:en",
        q='(Colusa OR Glenn OR "Sacramento Valley" OR "Glenn-Colusa") AND rice AND (drought OR fallow* OR allocation OR "Central Valley Project")',
        gdelt='(Colusa OR Glenn OR "Sacramento Valley") rice (drought OR fallowing OR fallow OR allocation OR "Central Valley Project")',
        place=["colusa", "glenn", "sacramento valley", "glenn-colusa"], dataset="smap_l3"),
    "car_2023_wet": dict(
        preset="car_colusa_rice", start="2022-12-20", end="2023-11-15", hl="en-US", gl="US", ceid="US:en",
        q='("Sacramento Valley" OR Colusa OR Glenn) AND (rice OR farm*) AND ("atmospheric river" OR flood* OR "late planting")',
        gdelt='("Sacramento Valley" OR Colusa OR Glenn) (rice OR farm OR farmers) ("atmospheric river" OR flood OR flooding OR "late planting")',
        # used ONLY because the exact spec query returns 0 Google News items; documented in README
        q_fallback='("Sacramento Valley" OR Colusa OR Glenn) AND rice AND (flood* OR "atmospheric river" OR "late planting" OR harvest OR planting)',
        place=["colusa", "glenn", "sacramento valley"], dataset="imerg_daily"),
    "caf_2023_flood": dict(
        preset="caf_tulare_forage", start="2023-03-01", end="2023-08-31", hl="en-US", gl="US", ceid="US:en",
        q='("Tulare Lake" OR Kings County OR Corcoran OR Tulare) AND (flood* OR "atmospheric river") AND (dairy OR farm* OR alfalfa OR crop*)',
        gdelt='("Tulare Lake" OR "Kings County" OR Corcoran OR Tulare) (flood OR flooding OR "atmospheric river") (dairy OR farm OR farms OR alfalfa OR crops)',
        place=["tulare", "kings county", "corcoran"], dataset="imerg_daily"),
    "caf_2024_sgma": dict(
        preset="caf_tulare_forage", start="2024-03-01", end="2024-06-30", hl="en-US", gl="US", ceid="US:en",
        q='("Tulare Lake" subbasin OR "Kings County") AND (probation OR SGMA OR groundwater)',
        gdelt='("Tulare Lake" OR "Kings County") (probation OR SGMA OR groundwater)',
        place=["tulare", "kings county"], dataset="grace_gw"),
    "bc_salmon_2023": dict(
        preset="bc_opener", start="2023-06-01", end="2023-10-15", hl="en-CA", gl="CA", ceid="CA:en",
        q='("Salmon River" OR Shuswap OR "Salmon Arm" OR Westwold OR "Bessette Creek") AND (drought OR "fish protection order" OR curtail* OR "fish population protection") AND (farm* OR forage OR hay OR irrigation OR rancher*)',
        gdelt='("Salmon River" OR Shuswap OR "Salmon Arm" OR Westwold OR "Bessette Creek") (drought OR "fish protection order" OR curtailment OR "fish population protection") (farm OR forage OR hay OR irrigation OR rancher)',
        place=["salmon river", "shuswap", "salmon arm", "westwold", "bessette", "thompson okanagan", "thompson-okanagan"], dataset="smap_l3"),
    "bc_sumas_2021": dict(
        preset="bc_opener", start="2021-11-10", end="2021-12-31", hl="en-CA", gl="CA", ceid="CA:en",
        q='("Sumas Prairie" OR Abbotsford OR "Fraser Valley") AND ("atmospheric river" OR flood*) AND (farm* OR dairy OR blueberr* OR livestock)',
        gdelt='("Sumas Prairie" OR Abbotsford OR "Fraser Valley") ("atmospheric river" OR flood OR flooding) (farm OR farms OR dairy OR blueberry OR livestock)',
        place=["sumas", "abbotsford", "fraser valley"], dataset="imerg_daily"),
}
OUTPUT = {"car_colusa_rice": ["car_2022_drought", "car_2023_wet"],
          "caf_tulare_forage": ["caf_2023_flood", "caf_2024_sgma"],
          "bc_opener": ["bc_salmon_2023", "bc_sumas_2021"]}
# Pages already cited in planner-spec.md A1 (fetched directly for title/date).
CITED = {
    "bc_salmon_2023": ["https://news.gov.bc.ca/releases/2023FOR0052-001305"],
    "bc_sumas_2021": ["https://www.countrylifeinbc.com/catastrophic-flooding-hits-fraser-valley/", "https://www.cbc.ca/lite/story/1.6261829"],
    "caf_2023_flood": ["https://www.nbcnews.com/science/science-news/dormant-california-lake-reappeared-isnt-going-anywhere-fast-rcna92452"],
    "caf_2024_sgma": ["https://water.waterboards.ca.gov/press_room/press_releases/2024/pr20240415-tulare-lake-probationary-hearing.html"],
    "car_2023_wet": ["https://www.agalert.com/california-ag-news/archives/january-3-2024/later-rice-harvest-deals-minor-yield-quality-impacts/"],
    "car_2022_drought": ["https://science.nasa.gov/earth/earth-observatory/a-rough-year-for-rice-in-california-150412/"],
}
GOV = ("ca.gov", "usda.gov", "news.gov.bc.ca", "gov.bc.ca", "nasa.gov")
FARM = ("agalert.com", "farmprogress.com", "countrylifeinbc.com", "sjvwater.org")
