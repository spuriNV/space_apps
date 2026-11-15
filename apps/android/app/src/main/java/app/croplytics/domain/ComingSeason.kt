package app.croplytics.domain

import app.croplytics.data.remote.dto.OutlookDto
import app.croplytics.data.remote.dto.OutlookSeasonDto
import kotlin.math.roundToInt

data class OutlookRow(val months: String, val rain: String, val temperature: String)

data class ComingSeasonSummary(
    val lede: String,
    /** Exactly the three farmer items: rain outlook, water supply, next season's water need. */
    val items: List<Answer>,
    val outlookRows: List<OutlookRow>,
    val bareWindow: String?,
    val longSummary: String?,
    val notYetPublished: List<String>,
)

object ComingSeasonBuilder {
    private const val LETTERS = "JFMAMJJASOND"

    /** "NDJ" to "Nov–Jan". */
    fun seasonMonths(code: String): String {
        if (code.length != 3) return code
        for (i in 0 until 12) {
            val match = (0 until 3).all { LETTERS[(i + it) % 12] == code[it] }
            if (match) return "${Fmt.monthShort(i + 1)}–${Fmt.monthShort(i + 3)}"
        }
        return code
    }

    private fun lean(category: String?, prob: Double?, wet: String, dry: String): String {
        val p = prob?.roundToInt()
        return when {
            category == null -> "no outlook"
            category.startsWith("above") -> if (p != null && p < 40) "barely leans $wet ($p% chance)" else "leans $wet${p?.let { " ($it% chance)" } ?: ""}"
            category.startsWith("below") -> if (p != null && p < 40) "barely leans $dry ($p% chance)" else "leans $dry${p?.let { " ($it% chance)" } ?: ""}"
            else -> "no lean either way"
        }
    }

    private fun rainLean(s: OutlookSeasonDto) = lean(s.precipitation?.category, s.precipitation?.probability?.value, "wetter than normal", "drier than normal")
    private fun tempLean(s: OutlookSeasonDto) = lean(s.temperature?.category, s.temperature?.probability?.value, "warmer than normal", "cooler than normal")

    private val droughtWords = mapOf(
        "D0" to "abnormally dry", "D1" to "in moderate drought", "D2" to "in severe drought",
        "D3" to "in extreme drought", "D4" to "in exceptional drought",
    )

    fun build(o: OutlookDto, limit: Double?, limitIsExample: Boolean, shortName: (String, String) -> String): ComingSeasonSummary {
        val seasons = o.cpc?.seasons.orEmpty().sortedBy { it.lead }
        val winter = seasons.take(3)

        // 1. rain outlook
        val wetLeans = winter.count { it.precipitation?.category?.startsWith("above") == true }
        val dryLeans = winter.count { it.precipitation?.category?.startsWith("below") == true }
        val rainHeadline = when {
            winter.isEmpty() -> "No rain outlook published yet"
            wetLeans > dryLeans -> "Wetter than normal this winter"
            dryLeans > wetLeans -> "Drier than normal this winter"
            else -> "No clear lean this winter"
        }
        val usdm = o.drought?.usDroughtMonitor
        val droughtNow = usdm?.worstCategoryCode?.let { code ->
            "Drought Monitor: ${droughtWords[code] ?: "no drought"} in ${o.county ?: "the county"} (map of ${Fmt.date(usdm.mapDate)})."
        } ?: if (usdm?.worstCategory != null) "Drought Monitor: no drought in ${o.county ?: "the county"}." else null
        val droughtOutlook = o.drought?.cpcDroughtOutlook?.seasonal?.let {
            if (it.category?.contains("No_Drought", true) == true || it.category?.contains("none", true) == true) "No drought expected through ${it.target}."
            else "Drought outlook through ${it.target}: ${it.category?.replace('_', ' ')?.lowercase()}."
        }
        val rainItem = Answer(
            question = "Will it be a wet winter?",
            headline = rainHeadline,
            detail = (winter.joinToString(" ") { "${seasonMonths(it.season)}: rain ${rainLean(it)}." } + " " +
                listOfNotNull(droughtNow, droughtOutlook).joinToString(" ")).trim(),
            cite = "NOAA 3-month outlooks${o.cpc?.issued?.let { ", issued ${Fmt.date(it)}" } ?: ""}; US Drought Monitor.",
        )

        // 2. water supply
        val res = o.reservoirsNow.values.filter { it.pctOfAverage?.value != null }
        val avg = res.mapNotNull { it.pctOfAverage?.value }.average().takeIf { !it.isNaN() }
        val supplyHeadline = when {
            avg == null -> "Reservoir storage not available"
            avg >= 100 -> "Reservoirs above average for the date"
            avg >= 85 -> "Reservoirs a little below average for the date"
            else -> "Reservoirs below average for the date"
        }
        val resLine = res.joinToString("; ") { r ->
            "${r.name?.lowercase()?.replaceFirstChar(Char::titlecase) ?: "Reservoir"} ${r.pctOfAverage?.value?.roundToInt()}% of average" +
                (r.pctOfCapacity?.value?.let { " (${it.roundToInt()}% full)" } ?: "")
        }
        val cvp = o.allocations?.cvp?.wy2026.orEmpty()
        val cvpParts = listOfNotNull(
            cvp["north_of_delta_ag"]?.value?.let { "farms north of the Delta ${it.roundToInt()}%" },
            cvp["south_of_delta_ag"]?.value?.let { "south of the Delta ${it.roundToInt()}%" },
            cvp["sacramento_river_settlement_contractors"]?.value?.let { "Sacramento River settlement contractors ${it.roundToInt()}%" },
        )
        val swp = o.allocations?.swp?.latest?.value?.roundToInt()
        val allocLine = buildString {
            if (cvpParts.isNotEmpty()) append("This year's federal allocations: ${FieldNames.andList(cvpParts)}. ")
            if (swp != null) append("State Water Project: $swp%. ")
            val notYet = listOfNotNull(
                o.allocations?.cvp?.wy2027Initial?.status?.takeIf { it.contains("not", true) }?.let { "federal" },
                o.allocations?.swp?.wy2027Initial?.status?.takeIf { it.contains("not", true) }?.let { "state" },
            )
            if (notYet.isNotEmpty()) append("Next year's ${FieldNames.andList(notYet)} allocations are not announced yet.")
        }.trim()
        val reportDate = o.reservoirsNow.values.firstNotNullOfOrNull { it.reportDate }
        val supplyItem = Answer(
            question = "How much water is in storage?",
            headline = supplyHeadline,
            detail = listOf(resLine.takeIf { it.isNotBlank() }?.let { "$it." }, allocLine.takeIf { it.isNotBlank() }).filterNotNull().joinToString(" "),
            cite = "CDEC${reportDate?.let { ", ${Fmt.date(it)}" } ?: ""}; Reclamation and DWR allocations.",
            warn = avg != null && avg < 85,
        )

        // 3. next season's water need
        val strategies = o.irrigation2027?.strategies.orEmpty()
        val base = strategies.firstOrNull { it.isBaseline }
        val baseNeed = base?.irrigationNeedAfAc?.value
        val lowest = strategies.filter { !it.isBaseline && it.irrigationNeedAfAc?.value != null }.minByOrNull { it.irrigationNeedAfAc!!.value!! }
        val needItem = if (baseNeed != null) {
            val over = limit != null && baseNeed > limit
            val lo = base.engineParamRange?.low
            val hi = base.engineParamRange?.high
            Answer(
                question = "How much water will next season need?",
                headline = when {
                    limit == null -> "About ${Fmt.one(baseNeed)} acre-feet per acre with today's rotation"
                    over -> "About ${Fmt.one(baseNeed)} acre-feet per acre: ${Fmt.one(baseNeed - limit)} over your limit"
                    else -> "About ${Fmt.one(baseNeed)} acre-feet per acre: within your limit"
                },
                detail = buildString {
                    append("Today's rotation, with this winter's outlook")
                    if (lo != null && hi != null) append(", likely ${Fmt.one(lo)} to ${Fmt.one(hi)}")
                    append(". ")
                    if (limit != null) append("Limit ${Fmt.one(limit)}${if (limitIsExample) " (example)" else ""}. ")
                    lowest?.let { append("${shortName(it.id, it.name)}: ${Fmt.one(it.irrigationNeedAfAc!!.value!!)}.") }
                }.trim(),
                cite = "Rotation model with NASA POWER weather, shifted by NOAA's outlook.",
                glossaryIds = listOf("water_balance"),
                warn = over,
            )
        } else {
            Answer(
                question = "How much water will next season need?",
                headline = "Not worked out for this field yet",
                detail = "The rotation model has not been run with this winter's outlook.",
                cite = "Rotation model with NASA POWER weather.",
            )
        }

        // more detail
        val rows = seasons.map { OutlookRow(seasonMonths(it.season), "Rain ${rainLean(it)}", "Temperature ${tempLean(it)}") }
        val fe = o.fieldExpectations
        val bareWindow = fe?.bareWindow?.let { bw ->
            val start = Fmt.monthDayWords(bw.medianStart)
            val end = Fmt.monthDayWords(bw.medianEnd)
            if (start == null || end == null) return@let null
            val days = bw.medianDays?.value?.roundToInt()
            val chance = fe.heavyRainInWindow?.chanceClimatology?.value?.roundToInt()
            val chanceOutlook = fe.heavyRainInWindow?.chanceGivenOutlook?.value?.roundToInt()
            "Usually bare from $start to $end" + (days?.let { ", about $it days" } ?: "") + ". " +
                (chance?.let { "A day with 1 inch of rain or more landed in that window in $it% of past winters" } ?: "") +
                (chanceOutlook?.let { "; about $it% with this winter's outlook." } ?: ".") + " $BARE_DEFINITION"
        }
        return ComingSeasonSummary(
            lede = "An outlook, not a forecast.",
            items = listOf(rainItem, supplyItem, needItem),
            outlookRows = rows,
            bareWindow = bareWindow,
            longSummary = o.plainLanguageSummary,
            notYetPublished = o.blocked.map { "${it.item}: ${it.status ?: "not available"}" },
        )
    }
}
