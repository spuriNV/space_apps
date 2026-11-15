package app.croplytics.domain

import app.croplytics.data.remote.dto.NasaDatasetDto

// Fixed editorial content, word for word from the web app (frontend/app/src: nasa.ts, mock/datasets.json, mock/bc.json,
// components/ui/Sources.tsx, components/ui/What.tsx). Kept here so the phone and the web say the same things.

// ---------------- "NASA data behind this field" (nasa.ts) ----------------

enum class NasaStatus(val words: String, val rank: Int, val order: Int) {
    Live("Live.", 3, 0), Saved("Downloaded; not on screen yet.", 2, 2), Example("Example numbers on screen until it is wired in.", 1, 1), Pending("Not downloaded yet.", 0, 3)
}

data class NasaDataset(val id: String, val name: String, val agency: String, val tells: String, val scale: String, val usedFor: String, val status: NasaStatus)

object Nasa {
    private val FALLBACK = mapOf(
        "hls" to NasaStatus.Saved, "landsat" to NasaStatus.Live, "power" to NasaStatus.Live, "smap" to NasaStatus.Example, "grace" to NasaStatus.Example,
        "imerg" to NasaStatus.Saved, "opera" to NasaStatus.Saved, "modis" to NasaStatus.Pending, "ecostress" to NasaStatus.Pending, "nasadem" to NasaStatus.Saved, "iss" to NasaStatus.Live,
    )
    private data class Entry(val id: String, val name: String, val agency: String, val tells: String, val scale: String, val usedFor: String)
    private val CATALOGUE = listOf(
        Entry("hls", "Harmonized Landsat Sentinel-2 (HLS)", "NASA / USGS", "Whether the field is bare, green or flooded, every 2 to 3 days.", "100 ft squares (30 m)", "Field calendar"),
        Entry("landsat", "Landsat 8 and 9", "NASA / USGS", "Green cover and bare ground on this field since 2016.", "100 ft squares (30 m)", "Field calendar, green cover"),
        Entry("power", "NASA POWER weather", "NASA Langley", "Daily sun, wind and humidity, which set how much water a crop uses.", "one reading for about 35 miles (0.5°)", "Crop water use"),
        Entry("smap", "SMAP soil moisture", "NASA JPL", "Whether the root zone is wetter or drier than usual for the date.", "one reading for a 6-mile square (9 km)", "Soil moisture answer, 3D view"),
        Entry("grace", "GRACE-FO groundwater", "NASA / GFZ", "Whether groundwater in the basin is above or below usual. Basin-wide, not your own well.", "one reading for a 17-mile square (0.25°)", "Groundwater answer, 3D view"),
        Entry("imerg", "GPM IMERG rainfall", "NASA / JAXA", "Daily rain over the field, filling the gaps between weather stations.", "one reading for a 6-mile square (0.1°)", "Rain check against stations"),
        Entry("opera", "OPERA surface water", "NASA JPL", "When the field held standing water, such as winter flooding of rice.", "100 ft squares (30 m)", "Flooded days in the calendar"),
        Entry("modis", "MODIS greenness", "NASA", "How green the area was against normal, back to 2000.", "800 ft squares (250 m)", "Long-term greenness"),
        Entry("ecostress", "ECOSTRESS", "NASA JPL, on the Space Station", "Crop water stress from leaf temperature.", "230 ft squares (70 m)", "Crop stress"),
        Entry("nasadem", "NASADEM elevation", "NASA JPL", "Slope, and low spots where water ponds or frost settles.", "100 ft squares (30 m)", "Slope and low spots"),
        Entry("iss", "Astronaut photos from the ISS", "NASA Johnson Space Center", "What the valley around the field looked like from orbit.", "photo, about 400 mm lens", "Photo on this panel"),
    )
    private val ALIAS = mapOf(
        "smap_l3" to "smap", "smap_l4" to "smap", "dem" to "nasadem", "dswx" to "opera", "opera_dswx" to "opera", "gpm_imerg" to "imerg",
        "grace_fo" to "grace", "nasa_power" to "power", "iss_photos" to "iss",
    )
    private fun toStatus(s: String?): NasaStatus? = when (s?.lowercase()) {
        null, "" -> null
        "live", "real", "served", "on_screen" -> NasaStatus.Live
        "saved", "cached", "downloaded", "fetched", "computed" -> NasaStatus.Saved
        "example", "fixture", "mock" -> NasaStatus.Example
        else -> NasaStatus.Pending
    }

    /** The list for one field: the API's status, upgraded to Live where this app shows the data from real readings. */
    fun list(apiNasa: List<NasaDatasetDto>, backendStatus: Map<String, String?>, used: Map<String, NasaStatus>): List<NasaDataset> {
        val status = FALLBACK.toMutableMap()
        for ((k, v) in backendStatus) {
            val id = ALIAS[k] ?: k
            val cur = status[id] ?: continue
            if (v == "real" && cur.rank < NasaStatus.Saved.rank && cur != NasaStatus.Example) status[id] = NasaStatus.Saved
        }
        val seen = mutableMapOf<String, NasaStatus>()
        for (it in apiNasa) {
            val raw = it.id.lowercase(); val id = ALIAS[raw] ?: raw
            var st = toStatus(it.status) ?: continue
            if (id !in FALLBACK) continue
            if (st == NasaStatus.Live && FALLBACK[id] != NasaStatus.Live) st = NasaStatus.Saved
            if (seen[id] == null || st.rank > seen[id]!!.rank) seen[id] = st
        }
        status.putAll(seen)
        for ((id, st) in used) if (st.rank > (status[id] ?: NasaStatus.Pending).rank) status[id] = st
        return CATALOGUE.map { NasaDataset(it.id, it.name, it.agency, it.tells, it.scale, it.usedFor, status[it.id] ?: NasaStatus.Pending) }
            .sortedBy { it.status.order }
    }
}

// ---------------- map layers (mock/datasets.json) ----------------

data class MapDataset(
    val id: String, val name: String, val longName: String, val sees: String, val nativeScale: String, val footprintM: Double,
    val cadence: String, val since: Int, val regional: Boolean, val color: String, val inStack: String? = null, val caveat: String? = null,
)

object MapDatasets {
    val ALL = listOf(
        MapDataset("hls", "HLS", "Harmonized Landsat Sentinel-2", "Cover, greenness, open water", "30 m", 30.0, "2–3 days", 2013, false, "#7ee081", "surface"),
        MapDataset("ecostress", "ECOSTRESS", "ECOSTRESS on the Space Station", "Land-surface temperature, crop water use", "70 m", 70.0, "irregular", 2018, false, "#ffb454"),
        MapDataset("modis", "MODIS", "MODIS vegetation indices (MOD13Q1)", "Greenness history since 2000", "250 m", 250.0, "16 days", 2000, false, "#c3e88d"),
        MapDataset("smap", "SMAP", "Soil Moisture Active Passive (L3 / L4)", "Surface and root-zone soil moisture", "9 km", 9000.0, "daily", 2015, true, "#5ab0ff", "soil"),
        MapDataset("imerg", "IMERG", "GPM IMERG precipitation", "Rain and storms", "~10 km", 10000.0, "daily", 2000, true, "#9d8cff"),
        MapDataset("grace", "GRACE", "GRACE / GRACE-FO drought indicators", "Groundwater storage percentile", "0.25°", 27800.0, "weekly", 2003, true, "#ff7eb6", "groundwater", "Underlying signal is about 300 km wide"),
    )
    /** Layers on by default (App.tsx). */
    val DEFAULT_ON = mapOf("hls" to true, "smap" to true, "grace" to true, "imerg" to false, "modis" to false, "ecostress" to false)
}

// ---------------- "Why not BC yet" (mock/bc.json) ----------------

data class BCPlace(val name: String, val lat: Double, val lon: Double)

object BC {
    const val TITLE = "Why not BC yet"
    const val INTRO = "The idea started in British Columbia: the August 2023 Salmon River forage-water orders and the November 2021 Sumas Prairie flood. The ground data there is too thin to check a field-level answer, so the tool is built and tested in California first."
    val LINES = listOf(
        "No OpenET" to "Field-scale measured crop water use covers western US states only.",
        "No field-soil API" to "BC soil comes from survey polygons or a 250 m global model.",
        "One station per valley" to "Salmon Arm CS is the only active daily weather station in its valley.",
        "Crop labels since 2011" to "AAFC crop inventory starts in 2011, with thin BC ground sampling in 2021.",
    )
    const val LIMIT = "BC is out of scope; transferability is a claim to test."
    val PLACES = listOf(BCPlace("Salmon River / Shuswap", 50.62, -119.33), BCPlace("Sumas Prairie", 49.06, -122.17))
    const val NEXT = "Next step: BC appendix"
    const val NEXT_REF = "planner-spec.md, Appendix A"
}

// ---------------- Sources (components/ui/Sources.tsx) ----------------

object Sources {
    val GROUPS = listOf(
        "NASA" to listOf(
            "HLS (Harmonized Landsat Sentinel-2), NASA/USGS" to "Bare, green or flooded every few days; the field calendar. 30 m.",
            "Landsat 8 and 9, NASA/USGS" to "Greenness since 2016, inside HLS and the 3D view. 30 m.",
            "GPM IMERG, NASA/JAXA" to "Daily rain over the field; rain since 1 Oct and its 2001–2025 normal. 0.1°.",
            "GRACE-FO data assimilation, NASA" to "Groundwater and root-zone soil moisture percentiles, weekly, run through a land model. One reading for a 17-mile square; the satellites themselves sense about 190 miles. Groundwater is the whole basin, not your own well.",
            "SMAP, NASA" to "Root-zone soil moisture, one reading for a 6-mile square, when its readings are in.",
            "OPERA surface water (DSWx), NASA JPL" to "Standing water on the field in each clear image. 30 m.",
            "NASA POWER" to "Sun, wind and humidity for crop water use (the rotation model). 0.5°.",
            "NASADEM, NASA JPL" to "Slope and low spots. 30 m.",
            "Astronaut photography, NASA Johnson Space Center" to "The ISS photo of the valley. Image courtesy of the Earth Science and Remote Sensing Unit, NASA Johnson Space Center.",
        ),
        "Other satellites" to listOf(
            "Sentinel-2, ESA (Copernicus)" to "100 ft squares in the 3D view; also inside HLS. 10–20 m.",
            "OpenET ensemble" to "Measured crop water use on this field, monthly, 2016–2025; the check on our model.",
        ),
        "Ground data" to listOf(
            "NOAA weather stations (GHCN-Daily)" to "Hot days (104 °F), frost nights, heavy-rain days.",
            "USDA Cropland Data Layer" to "The crop grown each year, 2008–2025.",
            "USDA soil survey (SSURGO)" to "Soil type, sand, silt and clay (top 3 feet), water held, drainage, salt.",
            "DWR / Land IQ crop mapping 2023" to "The field outline and state field number.",
            "USDA Risk Management Agency" to "Crop-insurance payouts by county, crop and cause.",
            "NOAA Climate Prediction Center, US Drought Monitor" to "Winter outlooks and drought, county.",
            "California Data Exchange Center (CDEC), Reclamation, DWR" to "Reservoir storage, allocations, snowpack.",
        ),
        "Models" to listOf(
            "CropLytics rotation model" to "FAO-56 crop water use and the rules of thumb for soil, feed and pests; weather 2015–2025.",
            "Bare / green / flooded rule" to "Greenness below 0.2 is bare, 0.2–0.35 thin; water index for flooding.",
            "Machine-learning calendar (random forest)" to "A second opinion on the rule, trained on neighbouring fields; tested on 2022.",
            "Crop-stress weeks" to "Two statistical methods on greenness, heat and dry air, growing season only.",
        ),
    )
    const val FOOT = "Every number in CropLytics comes from one of these, or is marked as our assumption. It supports the grower and adviser; it does not replace either."
}

// ---------------- "What's this?" (components/ui/What.tsx) ----------------

enum class Gloss(val term: String, val text: String, val apiKey: String) {
    Et("Crop water use (evapotranspiration, ET)", "The water a crop pulls from the soil and gives off through its leaves, plus what evaporates from the ground. It is what irrigation and rain have to replace. Measured in inches, or acre-feet per acre (1 acre-foot per acre = 12 inches).", "et"),
    Greenness("Greenness (NDVI)", "How green the field looks from a satellite, on a 0 to 1 scale. Bare soil is below 0.2, a young or thin crop 0.2 to 0.35, and a full green canopy above 0.6. Standing water reads near 0.", "ndvi"),
    SoilAnomaly("Soil moisture against normal", "Whether the top few feet of soil hold more or less water than usual for this time of year, ranked against the same dates in other years. 50 is a normal year; 90 means wetter than 9 years in 10. One reading covers several miles, not your field alone.", "soil_moisture_pct"),
    Frost("Frost risk", "Nights when the air near the ground drops to 32 °F or lower at the weather stations near the field. Low spots in a field can be a few degrees colder than the station.", "frost"),
    WaterBalance("Water balance (irrigation need)", "Crop water use minus the rain that soaks in and stays in the root zone. What is left is the irrigation the crop needs, before losses in the ditch or the system.", "water_balance"),
    Bare("Bare days", "Days the satellites see bare ground: greenness below 0.2 and no standing water. Bare soil in heavy rain loses topsoil; bare soil in heat dries out and crusts.", "cover_classes"),
    Opera("Standing water seen (NASA OPERA)", "NASA’s OPERA product marks every 100 ft square that holds open or shallow water in each clear Landsat or Sentinel-2 image. It sees winter flooding that a greenness reading can miss.", "dswx"),
    Stress("Crop-stress weeks", "Growing-season weeks when the crop was greener than nothing but under strain: unusual heat, very thirsty air, or weaker growth than in its other years. Two statistical methods look for them; a week counts when either flags it.", "stress"),
    RuleMl("Rule and machine learning", "The rule calls a field bare below greenness 0.2 and flooded when the water index is high. The machine-learning version learns the same classes from neighbouring fields. We show both and say how often each was right in 2022, a year neither trained on.", "rule_vs_ml"),
    Heat("Hot days", "Days when the weather stations near the field reach 104 °F or more. Above that, most crops close their leaves and stop growing, and bare soil bakes.", "heat_days"),
}
