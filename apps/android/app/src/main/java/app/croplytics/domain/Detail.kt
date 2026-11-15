package app.croplytics.domain

import app.croplytics.data.remote.dto.InsuranceDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.ModelsDto
import app.croplytics.data.remote.dto.OpenEtDto
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.remote.dto.StressDto
import app.croplytics.data.remote.dto.WaterSeenDto
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.doubleOrNull
import kotlin.math.roundToInt

/** Plain lines for the "More detail" sections, built from whatever the API returns. */
object DetailBuilder {

    /** About the field: soil, water it holds, drainage, salt, slope, water source. */
    fun about(loc: LocationDto): List<Pair<String, String>> = buildList {
        val s = loc.soil
        if (s != null) {
            s.muname?.let { add("Soil" to it.substringBefore(",") + (s.textureClass?.let { t -> ", ${t.lowercase()}" } ?: "")) }
            s.awcMmPerM?.value?.let { awc ->
                val inPerFt = awc / 1000 * 12
                add("Holds" to "${Fmt.one(inPerFt)} in of water per foot of soil" + when { inPerFt < 1.4 -> " (low: needs frequent, short irrigations)"; inPerFt > 2 -> " (high)"; else -> "" })
            }
            s.drainageClass?.let { add("Drainage" to it + (s.hydrologicGroup?.let { g -> "; runoff group $g" } ?: "")) }
            add(
                "Salt" to when (val ec = s.ecDsPerM) {
                    null -> "Not in the soil survey"
                    else -> (if (ec >= 4) "Salty soil; limits salt-sensitive crops" else "Low salt") + " (EC ${Fmt.one(ec)} dS/m)"
                },
            )
            s.omPct?.value?.let { add("Organic matter" to "${Fmt.one(it)}% in the top 3 feet") }
        }
        loc.terrain?.slopeMeanPct?.value?.let { slope ->
            val words = when { slope < 2 -> "Nearly flat"; slope < 5 -> "Gentle slope"; else -> "Sloping" }
            val low = loc.terrain.lowSpotFraction?.value?.let { "; low spots on about ${(it * 100).roundToInt()}% of the field, where water ponds and frost settles" } ?: ""
            add("Slope" to "$words, about ${Fmt.one(slope)}% on average$low")
        }
        loc.water?.let { w ->
            val src = if (w.source == "surface") "Surface water" else if (w.source != null) "Groundwater (wells)" else null
            val district = w.district?.takeUnless { it.contains("(U)") }
            if (src != null) add("Water" to src + (district?.let { ", $it" } ?: "") + (w.sgmaSubbasin?.let { "; $it groundwater subbasin" } ?: ""))
        }
        loc.dwrUniqueId?.let { add("State field no." to "$it (DWR / Land IQ crop map)") }
        add("Centre" to String.format(java.util.Locale.US, "%.4f° N, %.4f° W", loc.centroid.lat, kotlin.math.abs(loc.centroid.lon)))
    }

    fun crops(loc: LocationDto, from: Int = 2016): List<Pair<Int, String>> =
        FieldNames.history(loc).filterKeys { it >= from }.toSortedMap().map { (y, c) -> y to FieldNames.cropName(c) }

    fun stress(d: StressDto): List<String> {
        val years = d.summary?.byYear.orEmpty().mapNotNull { (y, v) -> y.toIntOrNull()?.let { it to v } }.sortedByDescending { it.first }
        if (years.isEmpty()) return listOf("No growing season checked yet.")
        return years.take(4).map { (y, v) ->
            val flagged = maxOf(v.flagZscore, v.flagIforest)
            "$y${v.crop?.let { " ($it)" } ?: ""}: $flagged of ${v.evaluated} growing-season weeks flagged as stressed by at least one method" +
                (if (v.flagZscore != v.flagIforest) " (${v.flagZscore} by the z-score check, ${v.flagIforest} by the isolation forest)." else ".")
        } + "Crop stress: two statistical methods on satellite greenness and NASA POWER heat and dryness, growing season only."
    }

    fun water(d: WaterSeenDto): List<String> = buildList {
        d.summary?.let(::add)
        d.seasons.filter { it.clearScenes > 0 }.takeLast(4).asReversed().forEach { s ->
            add("${s.season}: ${s.maxWaterFrac?.let { "up to ${(it * 100).roundToInt()}% under water" } ?: "no reading"} in ${s.clearScenes} clear views.")
        }
        add("NASA/JPL OPERA surface water, 100 ft squares, clear images only.")
    }

    private fun metric(m: kotlinx.serialization.json.JsonObject?, key: String) = (m?.get(key) as? JsonPrimitive)?.doubleOrNull

    /**
     * The machine-learning bare-field check, shown as a comparison next to the greenness rule (not as
     * the answer): accuracy on years each method never saw.
     */
    fun machineLearning(d: ModelsDto): List<String> {
        val bare = d.items.filter { it.task == "bare_cover" && it.id.contains("_year_v1") && !it.id.contains("spatial") }
        if (bare.isEmpty()) return listOf("No machine-learning check for this field yet.")
        val names = mapOf("rule_ndvi" to "Greenness rule (what the app shows)", "random_forest" to "Random forest", "hist_gbt" to "Gradient boosting")
        val years = bare.firstOrNull()?.split?.testYears.orEmpty()
        val lines = bare.mapNotNull { m ->
            val acc = metric(m.metrics, "accuracy") ?: return@mapNotNull null
            "${names[m.method] ?: m.method}: matched the crop record ${(acc * 100).roundToInt()}% of the time"
        }
        return listOf("Tested on years each method never saw${if (years.isNotEmpty()) " (${FieldNames.andList(years.map(Int::toString))})" else ""}:") + lines +
            "The models learn from the same crop record they are scored against, so their scores run high; the app keeps the simpler rule and shows these as a check."
    }

    fun openet(d: OpenEtDto, baseline: StrategyDto?): List<String> {
        val full = d.annual.filter { it.months == 12 && it.etMm != null }.takeLast(5).asReversed()
        if (full.isEmpty()) return listOf("No OpenET measurements for this field yet.")
        return full.map { "${it.year}: ${Fmt.one(Units.mmToInches(it.etMm!!))} in of water used (${Fmt.one(Units.mmToAfAc(it.etMm))} acre-ft/acre)" } +
            listOfNotNull(
                baseline?.water?.etcVsOpenetPct?.usable?.let { v ->
                    "Our model runs about ${kotlin.math.abs(v).roundToInt()}% ${if (v >= 0) "high" else "low"} against these measurements for today's crop."
                },
                "OpenET satellite measurement (ensemble of 6 models built on Landsat), monthly, this field's outline.",
            )
    }

    fun insurance(d: InsuranceDto): List<String> {
        val p = d.profiles.values.firstOrNull() ?: return listOf("No crop-insurance record for this county and crop.")
        val total = p.totalIndemnityUsd ?: return listOf("No crop-insurance record for this county and crop.")
        val top = p.byYear.maxByOrNull { it.value }
        val drought = p.shares["share_drought"]?.value
        val years = d.years.takeIf { it.size == 2 }?.let { "${it[0]} to ${it[1]}" } ?: ""
        return listOfNotNull(
            "${Fmt.usd(total)} paid out on ${p.scope ?: "county"} ${p.crop?.replace('_', ' ') ?: "crops"}${if (years.isNotEmpty()) ", $years" else ""}" +
                (top?.let { "; ${Fmt.usd(it.value)} in ${it.key} alone." } ?: "."),
            drought?.takeIf { it >= 0.3 }?.let { "${(it * 100).roundToInt()}% of it for drought or failed irrigation water." },
            "USDA Risk Management Agency, county totals, not this farm.",
        )
    }
}
