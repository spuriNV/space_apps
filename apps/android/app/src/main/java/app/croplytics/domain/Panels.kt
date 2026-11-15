package app.croplytics.domain

import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.NasaNowDto
import app.croplytics.data.remote.dto.OutlookCategoryDto
import app.croplytics.data.remote.dto.OutlookDto
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.remote.dto.StressDto
import app.croplytics.data.remote.dto.WaterSeenDto
import kotlin.math.abs
import kotlin.math.roundToInt

// ---------------- Coming season (ComingSeason.tsx) ----------------

object SeasonLogic {
    val SEASON = mapOf("OND" to "Oct–Dec", "NDJ" to "Nov–Jan", "DJF" to "Dec–Feb", "JFM" to "Jan–Mar", "FMA" to "Feb–Apr", "MAM" to "Mar–May", "AMJ" to "Apr–Jun")
    val DROUGHT = mapOf("No_Drought" to "No drought expected", "Persists" to "Drought likely to stay", "Improvement" to "Drought likely to ease", "Removal" to "Drought likely to end", "Development" to "Drought likely to develop")

    data class Lean(val words: String, val tilt: Int)
    fun lean(c: OutlookCategoryDto?, rain: Boolean): Lean {
        val cat = c?.category ?: return Lean("no lean either way", 0)
        if (cat.startsWith("equal")) return Lean("no lean either way", 0)
        val up = cat.startsWith("above"); val weak = (c.probability?.value ?: 40.0) <= 35
        val w = if (rain) (if (up) "wetter" else "drier") else (if (up) "warmer" else "cooler")
        return Lean("${if (weak) "barely leans" else "leans"} $w than normal", if (weak) 0 else if (up) 1 else -1)
    }
    fun maf(af: Double) = if (af >= 1e6) "${String.format(java.util.Locale.US, "%.2f", af / 1e6)} million acre-feet" else "${String.format(java.util.Locale.US, "%,d", (af / 1000).roundToInt())} thousand acre-feet"
    fun words(s: String) = s.lowercase().split(" ").joinToString(" ") { it.replaceFirstChar(Char::uppercase) }
    private fun band(v: Double, hi: String, mid: String, lo: String) = if (v >= 67) hi else if (v > 33) mid else lo

    data class View(
        val headline: String, val outlookTag: String?, val winterRain: String, val supply: String, val nextNeed: String,
        val outlookRows: List<Pair<String, String>>, val issued: String?, val droughtNow: String, val droughtOutlook: String,
        val reservoirs: List<Pair<String, String>>, val reservoirDate: String?,
        val rainSince: String, val rootSoil: String, val groundwater: String, val soilCite: String,
        val allocationsLead: String?, val storageRows: List<List<String>>, val shastaNow: String?, val snow: String,
        val bareTitle: String, val bareText: String, val bareCite: String,
        val needRows: List<NeedRow>, val needNote: String,
    )
    data class NeedRow(val name: String, val today: Boolean, val outlook: String?, val outlookOver: Boolean, val typical: String, val typicalOver: Boolean, val dry: String, val wet: String)

    fun build(loc: LocationDto, o: OutlookDto?, nasaNow: NasaNowDto?, regional: RegionalSeries?, strategies: List<StrategyDto>, cal: FieldCalendar?, daily: Daily?, limit: Double, example: Boolean, todayT: Int, notReady: Boolean): View {
        val soil = regional?.let { latestAt(it.soil, todayT, 14) }; val gw = regional?.let { latestAt(it.groundwater, todayT, 14) }
        val seasons = o?.cpc?.seasons.orEmpty().sortedBy { it.lead }
        val tilts = seasons.take(4).map { lean(it.precipitation, true).tilt }
        val wet = tilts.count { it > 0 }; val dry = tilts.count { it < 0 }
        val surface = loc.water?.source == "surface"
        val res = o?.reservoirsNow?.values.orEmpty().toList()
        val shasta = res.firstOrNull { it.name?.contains("shasta", true) == true } ?: res.firstOrNull()
        val pctAvg = { r: app.croplytics.data.remote.dto.ReservoirDto -> r.pctOfAverage?.value ?: r.pctOfOwnAverage?.value }
        val settlement = o?.allocations?.cvp?.wy2026?.get("sacramento_river_settlement_contractors")?.value
        val supply = when {
            o == null -> "Loading…"
            notReady && surface -> "Not ready for this field yet."
            surface -> listOfNotNull(shasta?.let { s -> pctAvg(s)?.let { "${words(s.name.orEmpty())}: ${it.roundToInt()}% of average." } }, settlement?.let { "Your allocation: ${it.roundToInt()}%." }).joinToString(" ")
            gw != null -> "Basin groundwater: ${band(gw.first, "above usual", "about usual", "below usual")}. Under state pumping rules."
            else -> "Groundwater reading not available right now."
        }
        val today = strategies.firstOrNull { it.isBaseline }
        val irr = o?.irrigation2027?.strategies.orEmpty().associateBy { it.id }
        val nxt = today?.let { irr[it.id]?.irrigationNeedAfAc?.value ?: it.water.irrigationNeedMm?.usable?.let { mm -> mm / 304.8 } }
        val nextNeed = nxt?.let { "Needs ${Fmt.one(it)} acre-ft/acre. Limit ${Fmt.one(limit)}${if (example) " (example)" else ""}. ${if (it > limit) "${Fmt.one(it - limit)} short." else "It fits."}" } ?: "Loading…"
        val headline = when { o == null -> "Loading the outlooks…"; notReady -> "Winter outlook not ready for this field yet"; wet > dry -> "Wetter than normal this winter"; dry > wet -> "Drier than normal this winter"; else -> "No clear lean this winter" }
        val winterRain = when { o == null -> "Loading…"; notReady -> "Not ready for this field yet."; wet > dry -> "Leans wetter than normal this winter."; dry > wet -> "Leans drier than normal this winter."; else -> "No clear lean either way this winter." }
        val dm = o?.drought?.usDroughtMonitor; val dOut = o?.drought?.cpcDroughtOutlook?.seasonal
        val now = nasaNow?.readings
        val rainMm = now?.get("imerg_wy_to_date_mm")?.value; val rainN = now?.get("imerg_wy_to_date_normal_mm")?.value
        val sva = o?.allocations?.storageVsAlloc
        val cvp = o?.allocations?.cvp?.wy2026.orEmpty(); val swp = o?.allocations?.swp?.latest
        val bw = o?.fieldExpectations?.bareWindow; val hr = o?.fieldExpectations?.heavyRainInWindow
        val (bareTitle, bareText) = when {
            bw?.medianStart != null -> {
                val start = Fmt.monthDayWords(bw.medianStart)?.let { shortMonth(it) }; val end = Fmt.monthDayWords(bw.medianEnd)?.let { shortMonth(it) }
                val leanWord = seasons.take(3).let { s -> if (s.count { it.precipitation?.category?.startsWith("above") == true } >= 2) "wetter, so the odds are a little higher" else if (s.count { it.precipitation?.category?.startsWith("below") == true } >= 2) "drier, so the odds are a little lower" else "neither way" }
                "Usually bare from $start to $end" to ("About ${(bw.medianDays?.value ?: 0.0).roundToInt()} days${bw.medianDays?.low?.let { " (${it.roundToInt()}–${(bw.medianDays.high ?: 0.0).roundToInt()} in past winters)" } ?: ""}. " +
                    "A day with 1 inch of rain or more landed in that window in ${(hr?.chanceClimatology?.value ?: 0.0).roundToInt()}% of past winters" + (if (hr?.chanceGivenOutlook?.value != null) "; this winter’s outlook leans $leanWord" else "") + ".")
            }
            o != null && bw == null -> {
                val b = cal?.let { SeasonCalc.bareWindow(it, daily, it.years.map { y -> y.year }.filter { y -> y in 2016..2025 }) }
                if (b != null && b.days > 0) "Usually bare from ${b.from} to ${b.to}" to "About ${b.days} days. ${if (b.chance != null) "In ${b.hits} of the last ${b.winters} winters at least one day with 1 inch of rain or more fell in that window." else ""}"
                else "Usually covered or flooded all winter: no regular bare stretch" to ""
            }
            o == null -> "Loading…" to ""
            else -> "Usually covered or flooded all winter: no regular bare stretch" to ""
        }
        val needRows = strategies.map { s ->
            val nn = s.water.irrigationNeedMm; val dr = s.exposure.replay["2022"]?.irrigationNeedMm; val wt = s.exposure.replay["2023"]?.irrigationNeedMm
            val v = nn?.usable ?: 0.0
            NeedRow(CompareLogic.shortName(s), s.isBaseline, irr[s.id]?.irrigationNeedAfAc?.value?.let { Fmt.one(it) }, (irr[s.id]?.irrigationNeedAfAc?.value ?: 0.0) > limit,
                "${Fmt.one((nn?.low ?: v) / 304.8)}–${Fmt.one((nn?.high ?: v) / 304.8)}", v / 304.8 > limit,
                dr?.value?.let { Fmt.one(it / 304.8) } ?: "–", wt?.value?.let { Fmt.one(it / 304.8) } ?: "–")
        }
        val spread = irr.values.mapNotNull { s -> s.irrigationNeedAfAc?.let { (it.high ?: 0.0) - (it.low ?: 0.0) } }.maxOrNull()
        return View(
            headline = headline, outlookTag = if (notReady) null else "An outlook, not a forecast.", winterRain = winterRain, supply = supply, nextNeed = nextNeed,
            outlookRows = seasons.take(4).map { s ->
                val r = lean(s.precipitation, true); val t = lean(s.temperature, false)
                (SEASON[s.season] ?: s.season) to "Rain ${r.words}${s.precipitation?.probability?.value?.let { " (${it.roundToInt()}% chance)" } ?: ""}. Temperature ${t.words}${s.temperature?.probability?.value?.let { " (${it.roundToInt()}%)" } ?: ""}."
            },
            issued = o?.cpc?.issued,
            droughtNow = dm?.let { "${if (it.worstCategory?.startsWith("None") == true || it.worstCategory == null) "No drought" else (it.worstCategory.replace(Regex("^D\\d "), "")).lowercase().replaceFirstChar(Char::uppercase)} in ${it.county ?: "${loc.countyName} County"} (map of ${Timeline.fmtDate(it.mapDate)})" } ?: "Not loaded",
            droughtOutlook = dOut?.let { "${DROUGHT[it.category] ?: it.category?.replace('_', ' ')} through ${it.target}" } ?: "Not loaded",
            reservoirs = res.map { r ->
                "${words(r.name.orEmpty())} reservoir" to listOfNotNull(pctAvg(r)?.let { "${it.roundToInt()}% of average for the date" }, r.pctOfCapacity?.value?.let { "${it.roundToInt()}% full" }).joinToString(", ") +
                    ". ${r.storageAf?.value?.let(::maf) ?: ""}${r.storageYearAgoAf?.value?.let { "; a year ago ${maf(it)}" } ?: ""}."
            },
            reservoirDate = res.firstOrNull()?.let { it.latestDailyDate ?: it.reportDate },
            rainSince = if (rainMm != null && rainN != null && rainN > 0) "${Fmt.one(rainMm / 25.4)} in, ${(rainMm / rainN * 100).roundToInt()}% of normal for the date" else "Not loaded",
            rootSoil = soil?.let { "${band(it.first, "Wetter than usual", "About normal", "Drier than usual")} (${Fmt.ordinal(it.first.roundToInt())} percentile, ${Timeline.when_(it.second)})" } ?: "Not loaded",
            groundwater = gw?.let { "${band(it.first, "Above usual", "About usual", "Below usual")} (${Fmt.ordinal(it.first.roundToInt())} percentile, ${Timeline.when_(it.second)}); whole basin, not your well" } ?: "Not loaded",
            soilCite = "NASA GPM IMERG rain (normal 2001–2025); NASA GRACE-FO ${if (regional?.soilSource == "smap") "groundwater and NASA SMAP soil moisture" else "with a land model, for soil and groundwater"}.",
            allocationsLead = if (surface && cvp.isNotEmpty()) "This year’s federal (Central Valley Project) allocations: Sacramento River settlement contractors ${cvp["sacramento_river_settlement_contractors"]?.value?.roundToInt()}%, farms north of the Delta ${cvp["north_of_delta_ag"]?.value?.roundToInt()}%, farms south of the Delta ${cvp["south_of_delta_ag"]?.value?.roundToInt()}%." +
                (swp?.value?.let { " State Water Project: ${it.roundToInt()}%${if (swp.source?.verified == false) " (from a news copy of the DWR release)" else ""}." } ?: "") else null,
            storageRows = if (surface) sva?.rows.orEmpty().filter { it.partial != true }.takeLast(6).map { r -> listOf("${r.allocationYear - 1}", "${(r.pctOfCapacity ?: 0.0).roundToInt()}%", "${r.southAg?.roundToInt() ?: "–"}%", "${r.settlement?.roundToInt() ?: "–"}%") } else emptyList(),
            shastaNow = sva?.shastaNowAf?.let { "${(it / 4552000 * 100).roundToInt()}%" },
            snow = (o?.snowpack?.snowNow?.let { "Statewide snowpack holds ${it.sweInches?.value ?: "?"} in of water (${it.reportDate}); the snow season has barely started. " } ?: "") +
                "DWR’s runoff forecast (Bulletin 120) is ${o?.snowpack?.bulletin120?.status ?: "not out yet"}; the first one usually comes in February.",
            bareTitle = bareTitle, bareText = bareText,
            bareCite = "${if (bw != null) "Longest bare run in this field’s satellite calendar each winter, and NOAA station rain 1981–2024." else "Satellite calendar of this field, winters 2016–2025, and rain from NOAA weather stations."} Past record, not a forecast. ${SeasonCalc.BARE_DEF}",
            needRows = needRows,
            needNote = "Acre-feet per acre a year. Your limit: ${Fmt.one(limit)}${if (example) " (example, change to yours on Compare)" else ""}; brown means over it. " +
                (spread?.let { if (it < 0.15) "In the model, this winter’s outlook moves irrigation need by ${if (it < 0.1) "less than 0.1" else "about 0.1"} acre-foot per acre: rain falls mostly before the crop needs water." else "Outlook range: up to ${Fmt.one(it)} acre-feet per acre between scenarios." } ?: ""),
        )
    }
    /** "mid February" -> "mid Feb" (web mdText). */
    private fun shortMonth(s: String) = s.split(" ").let { (p, m) -> "$p ${m.take(3)}" }
}

// ---------------- This field's year (YearSheet.tsx) ----------------

object YearLogic {
    val LABEL = mapOf('b' to "Bare", 'p' to "Thin cover", 'c' to "Crop growing", 'w' to "Flooded", 'u' to "No clear view")

    /** Most common cover for each 10-day step over the past years. */
    fun typical(years: List<CalYear>): String = buildString {
        for (d in 0 until 36) append(years.map { it.rule[d] }.filter { it != 'u' }.groupingBy { it }.eachCount().maxByOrNull { it.value }?.key ?: 'u')
    }

    data class Verdict(val short: String, val long: String)
    private fun pct(x: Double?) = x?.let { "${(it * 100).roundToInt()}%" } ?: "?"
    fun mlVerdict(ml: MLInfo?): Verdict {
        ml ?: return Verdict("Not ready for this field yet", "The machine-learning calendar is not ready for this field yet.")
        val agree = ml.disagreePct?.let { " The two disagree on ${it.roundToInt()}% of clear satellite days." } ?: ""
        return when {
            !ml.meetsTarget -> Verdict("Below accuracy target", "Below our accuracy target on this field: in 2022, a year it never trained on, it was right ${pct(ml.acc2022)} of the time against a target of 85%, and it misses bare ground too often. The rule calendar stays the answer; this is for comparison only.$agree")
            ml.inflated -> Verdict("Second opinion only", "In 2022, a year it never trained on, it scored ${pct(ml.acc2022)}. That is too good to take at face value: the model partly learned how its training labels were made. Shown as a second opinion next to the rule, not as the answer.$agree")
            else -> Verdict("Meets accuracy target", "Meets our accuracy target on this field (right ${pct(ml.acc2022)} of the time in 2022, a year it never trained on). Shown next to the rule as a comparison.$agree")
        }
    }

    data class Mark(val step: Int, val kind: String, val hit: Boolean = false, val title: String)
    data class Row(val year: Int, val crop: String, val rule: String, val ml: String, val current: Boolean, val bareDays: String, val rainOnBare: String, val marks: List<Mark>, val empty: Boolean)
    data class View(val sentence: String, val typical: String, val typicalLabel: String, val typicalBare: String, val rows: List<Row>, val verdict: Verdict)

    private fun count(rule: String, c: Char) = rule.count { it == c } * 10

    fun build(loc: LocationDto, cal: FieldCalendar, daily: Daily?, ml: MLInfo?, water: WaterSeenDto?, stress: StressDto?, t: Int, showEarlier: Boolean, detail: Boolean): View {
        val hist = FieldNames.history(loc)
        val cy = Timeline.yearOf(t)
        val last = Timeline.yearOf(Calendars.lastDataT(cal))
        val past = cal.years.filter { it.year <= last && it.rule.count { c -> c != 'u' } > 6 }
        val typ = typical(past)
        val ly = cal.year(last)
        val dBare = (ly?.let { count(it.rule, 'b') } ?: 0) - count(typ, 'b'); val dWater = (ly?.let { count(it.rule, 'w') } ?: 0) - count(typ, 'w')
        val diff = when {
            abs(dBare) >= 20 -> "$last had about ${abs(dBare)} ${if (dBare > 0) "more" else "fewer"} bare days than a typical year"
            abs(dWater) >= 20 -> "$last was flooded about ${abs(dWater)} days ${if (dWater > 0) "longer" else "less"} than a typical year"
            else -> "$last looked much like a typical year"
        }
        val up = ly?.greenup
        val thisYear = Timeline.yearOf(t).coerceAtLeast(last)
        val sentence = "$diff.${up?.let { " Green from ${Timeline.stepShort(it)}." } ?: ""}${if (last < thisYear) " ${last + 1} not processed yet." else ""}"
        fun rainDays(year: Int): List<Pair<String, Double>> = daily?.let { d -> d.dates.indices.filter { d.dates[it].startsWith("$year") }.mapNotNull { i -> (d.imerg[i] ?: d.stPrecip[i])?.takeIf { it >= 25.4 }?.let { d.dates[i] to it } } }.orEmpty()
        val rows = cal.years.filter { showEarlier || it.year >= Timeline.RECENT_FROM }.reversed().map { y ->
            val rd = rainDays(y.year)
            val hit = rd.count { (date, _) -> y.rule[Timeline.stepOf(Timeline.dateToT(date))] == 'b' }
            val empty = y.rule.all { it == 'u' }
            val marks = buildList {
                rd.forEach { (date, mm) -> val d = Timeline.stepOf(Timeline.dateToT(date)); add(Mark(d, "rain", y.rule[d] == 'b', "$date: ${Fmt.one(mm / 25.4)} in of rain, field ${LABEL[y.rule[d]]?.lowercase()}")) }
                if (detail) {
                    water?.scenes.orEmpty().filter { it.clear && it.date.startsWith("${y.year}") && (it.waterFrac ?: 0.0) >= 0.5 }.forEach { s ->
                        add(Mark(Timeline.stepOf(Timeline.dateToT(s.date)), "opera", title = "${Timeline.fmtDate(s.date)}: NASA OPERA saw ${((s.waterFrac ?: 0.0) * 100).roundToInt()}% of the field under water"))
                    }
                    stress?.weeks.orEmpty().filter { (it.status == "one" || it.status == "both") && it.weekStart.startsWith("${y.year}") }.forEach { w ->
                        add(Mark(Timeline.stepOf(Timeline.dateToT(w.weekStart)), "stress-${w.status}", title = "Week of ${Timeline.fmtDate(w.weekStart)}: crop stress, ${w.drivers.joinToString(" and ") { FieldNowLogic.DRIVER[it] ?: it }.ifBlank { "an unusual week" }}${w.tmaxC?.let { " (high ${(it * 9 / 5 + 32).roundToInt()} °F)" } ?: ""}. ${if (w.status == "both") "Both methods agree." else "One of two methods."}"))
                    }
                }
            }
            Row(y.year, hist[y.year]?.let(FieldNames::cropName) ?: "Crop map not out yet", y.rule, y.ml, y.year == cy,
                if (empty) "–" else SeasonCalc.bareDaysYear(y)?.toString() ?: "–", if (empty || daily == null) "–" else "$hit of ${rd.size}", marks, empty)
        }
        val typYear = CalYear(0, "", typ, typ, List(36) { 0.0 }, null, null)
        return View(sentence, typ, "most common, ${past.firstOrNull()?.year ?: ""}–${last.toString().takeLast(2)}", SeasonCalc.bareDaysYear(typYear)?.toString() ?: "–", rows, mlVerdict(ml))
    }
}

// ---------------- the winter bare window from the calendar (season.ts bareWindow) ----------------

fun SeasonCalc.bareWindow(cal: FieldCalendar, daily: Daily?, years: List<Int>): SeasonCalc.BareWindow? {
    val winter = listOf(30, 31, 32, 33, 34, 35, 0, 1, 2, 3, 4, 5, 6, 7, 8)
    val ys = cal.years.filter { it.year in years && it.rule.count { c -> c != 'u' } > 6 }
    if (ys.isEmpty()) return null
    val bare = winter.map { d ->
        var b = 0; var n = 0
        for (y in ys) { val yy = if (d >= 30) y else cal.year(y.year + 1); val c = yy?.rule?.getOrNull(d) ?: continue; if (c == 'u') continue; n++; if (c == 'b') b++ }
        if (n > 0) b.toDouble() / n else 0.0
    }
    var best: Pair<Int, Int>? = null; var i = 0
    while (i < winter.size) {
        if (bare[i] < 0.5) { i++; continue }
        var j = i; while (j + 1 < winter.size && bare[j + 1] >= 0.5) j++
        if (best == null || j - i > best.second - best.first) best = i to j
        i = j + 1
    }
    best ?: return SeasonCalc.BareWindow("", "", 0, null, 0, 0)
    val (a, b) = best; val d0 = winter[a]; val d1 = winter[b]
    var winters = 0; var hits = 0
    if (daily != null && daily.dates.isNotEmpty()) {
        val first = daily.dates.first(); val lastD = daily.dates.last()
        fun range(d: Int, yy: Int): Pair<String, String> { val m = d / 3; return "%04d-%02d-%02d".format(yy, m + 1, listOf(1, 11, 21)[d % 3]) to "%04d-%02d-%02d".format(yy, m + 1, if (d % 3 == 2) Timeline.monthEnd(m + 1, yy) else listOf(10, 20)[d % 3]) }
        for (y in first.take(4).toInt()..lastD.take(4).toInt()) {
            val from = range(d0, if (d0 >= 30) y else y + 1).first; val to = range(d1, if (d1 >= 30) y else y + 1).second
            if (from < first || to > lastD) continue
            val n = daily.dates.indices.count { k -> daily.dates[k] in from..to && (daily.stPrecip[k] ?: 0.0) >= 25.4 }
            winters++; if (n > 0) hits++
        }
    }
    return SeasonCalc.BareWindow(Timeline.stepShort(d0), Timeline.stepShort(d1), (b - a + 1) * 10, if (winters > 0) hits * 100.0 / winters else null, winters, hits)
}

// ---------------- Print for your adviser (RotationBrief.tsx) ----------------

object BriefLogic {
    private val SEASON = mapOf("NDJ" to "Nov–Jan", "DJF" to "Dec–Feb", "JFM" to "Jan–Mar", "FMA" to "Feb–Apr")
    private fun lean(c: OutlookCategoryDto?) = if (c?.category == null || c.category.startsWith("equal") || (c.probability?.value ?: 40.0) <= 35) "no clear lean" else if (c.category.startsWith("above")) "leans wetter than normal" else "leans drier than normal"
    /** Engine review notes are written for the team: strip spec references and convert mm to acre-feet per acre. */
    fun plain(t: String) = t.replace(Regex("\\s*\\((spec [^)]*|U)\\)"), "").replace(Regex("(\\d[\\d,]*)\\s?mm")) { m -> "${Fmt.one(m.groupValues[1].replace(",", "").toDouble() / 304.8)} acre-ft/acre" }

    data class TableRow(val name: String, val pick: Boolean, val need: String, val against: String, val bare: String, val hotBare: String)
    data class Brief(
        val prepared: String, val name: String, val sub: String, val option: String, val optionIsToday: Boolean,
        val thisField: String, val likely: List<String>, val optionTitle: String, val months: List<Triple<String, Char, String>>,
        val water: String, val waterStatus: String, val gains: List<String>?, val losses: List<String>?, val unclear: List<String>,
        val table: List<TableRow>, val checks: List<Pair<String, Boolean>>, val sources: String,
    )

    fun build(loc: LocationDto, strategies: List<StrategyDto>, pickId: String?, limit: Double, example: Boolean, o: OutlookDto?, nasaNow: NasaNowDto?, cal: FieldCalendar?, daily: Daily?, todayT: Int, todayLabel: String): Brief? {
        val s = strategies.firstOrNull { it.id == pickId } ?: strategies.firstOrNull { !it.isBaseline } ?: strategies.firstOrNull() ?: return null
        val base = strategies.firstOrNull { it.isBaseline } ?: strategies.first()
        val id = FieldNames.identity(loc); val hist = FieldNames.history(loc)
        val need = s.water.irrigationNeedMm; val needB = base.water.irrigationNeedMm
        fun afv(v: Double?) = v?.let { Fmt.one(it / 304.8) } ?: "–"
        val nv = need?.usable ?: 0.0
        val over = (need?.low ?: nv) / 304.8 > limit; val within = (need?.high ?: nv) / 304.8 <= limit
        val ctx = CompareLogic.ctx(strategies, daily, cal)
        val heavy = loc.soil?.hydrologicGroup == "D"
        val tr = if (s.isBaseline) null else CompareLogic.tradeoffs(base, s, ctx, strategies, heavy)
        val ob = SeasonCalc.observedBare(cal)
        val upper = Regex("safflower|wheat", RegexOption.IGNORE_CASE).containsMatchIn(s.name)
        val last = cal?.let { Timeline.yearOf(Calendars.lastDataT(it)) } ?: 2025
        val recent = listOf(last - 2, last - 1, last).joinToString(", ") { y -> "$y ${hist[y]?.let { FieldNames.cropName(it).lowercase() } ?: "(crop map not out yet)"}" }
        val soil = loc.soil; val inFt = soil?.awcMmPerM?.value?.let { it / 1000 * 12 }
        val soilName = soil?.muname?.substringBefore(",") ?: soil?.textureClass
        val soilBits = listOfNotNull(soil?.drainageClass?.lowercase(), inFt?.let { "holds about ${Fmt.one(it)} in of water per foot of soil" })
        val thisField = (soilName?.let { "$it${if (soilBits.isNotEmpty()) ": " + soilBits.joinToString(", ") else ""}${if ((soil?.ecDsPerM ?: 0.0) >= 4) ", salty enough to limit salt-sensitive crops" else ""}. " } ?: "") +
            "Water from ${if (loc.water?.source == "surface") "a surface-water district" else "wells, under a groundwater allocation"}. Last three seasons: $recent. " +
            (ob?.let { "Bare about ${it.value} days a year, mostly ${SeasonCalc.usuallyBareMonths(cal)} (satellite, ${it.years.first()}–${it.years.last()}). " } ?: "") + FieldNowLogic.openetText(strategies)
        val seasons = o?.cpc?.seasons.orEmpty().sortedBy { it.lead }
        val res = o?.reservoirsNow?.values?.firstOrNull()
        val rainMm = nasaNow?.readings?.get("imerg_wy_to_date_mm")?.value; val rainN = nasaNow?.readings?.get("imerg_wy_to_date_normal_mm")?.value
        val rain = daily?.let { SeasonCalc.rainSoFar(it, todayT) }
        val wet = seasons.count { it.precipitation?.category?.startsWith("above") == true }
        val bw = o?.fieldExpectations?.bareWindow
        val likely = buildList {
            if (seasons.isNotEmpty()) add("NOAA’s rain outlook: ${seasons.take(3).joinToString("; ") { "${SEASON[it.season] ?: it.season} ${lean(it.precipitation)}" }}.")
            o?.drought?.cpcDroughtOutlook?.seasonal?.let { d ->
                val now = o.drought?.usDroughtMonitor?.worstCategory?.let { c -> if (c.startsWith("None")) "no drought now" else "${c.replace(Regex("^D\\d "), "").lowercase()} now" } ?: ""
                add("Drought: $now; ${if (d.category == "No_Drought") "none expected" else d.category?.lowercase()} through ${d.target}.")
            }
            res?.let { add("${SeasonLogic.words(it.name.orEmpty())} reservoir is at ${(it.pctOfAverage?.value ?: it.pctOfOwnAverage?.value)?.let { p -> "${p.roundToInt()}% of average" } ?: "unknown"} for the date.") }
            if (rainMm != null && rainN != null && rainN > 0) add("Rain since 1 Oct: ${Fmt.one(rainMm / 25.4)} in, ${(rainMm / rainN * 100).roundToInt()}% of normal (NASA GPM IMERG satellite rain).")
            else rain?.let { add("Rain ${it.period.label}: ${SeasonCalc.fmtIn(it.inches)} in${it.pct?.let { p -> ", ${p.roundToInt()}% of normal" } ?: ""} (NASA GPM IMERG satellite rain).") }
            add(if (bw?.medianStart != null) "Longest bare stretch in winter: usually ${Fmt.monthDayWords(bw.medianStart)} to ${Fmt.monthDayWords(bw.medianEnd)}; a 1-inch rain day landed in it in ${(o.fieldExpectations?.heavyRainInWindow?.chanceClimatology?.value ?: 0.0).roundToInt()}% of past winters${if (wet > 0) ", and the outlook leans wet" else ""}."
                else "Usually covered or flooded all winter: no regular bare stretch.")
        }
        val ms = CompareLogic.monthStrip(s)
        val checks = s.brief.localReview.map { plain(it.item) to (it.severity == "high") } +
            ("This year’s water allocation or pumping limit, and any district rules on winter flooding or fallowing." to false) +
            ("Seed, buyer and price for the new crop: dollars are not counted in this summary." to false)
        return Brief(
            prepared = todayLabel, name = id.name, sub = "${id.acres ?: "?"} acres, ${id.county} County, California · ${id.stateFieldNo?.let { "state field no. $it" } ?: id.id}",
            option = CompareLogic.shortName(s), optionIsToday = s.isBaseline, thisField = thisField, likely = likely,
            optionTitle = s.name.replace(" (current)", ""), months = (0 until 12).map { Triple(Timeline.MONTHS[it], ms.cover[it], ms.months[it]) },
            water = "Irrigation need about ${afv(need?.value)} acre-feet per acre a year${if (upper) "*" else ""}${if (s.isBaseline) "" else ", against ${afv(needB?.value)} for what the field grows now"}. Your limit is ${Fmt.one(limit)}${if (example) " (an example limit; write in yours)" else ""}. In a dry year like 2022: ${afv(s.exposure.replay["2022"]?.irrigationNeedMm?.value)}.",
            waterStatus = if (over) "over the limit" else if (within) "fits" else "may go over",
            gains = tr?.gains, losses = tr?.losses, unclear = tr?.unclear.orEmpty(),
            table = strategies.map { x ->
                val nd = x.water.irrigationNeedMm; val v = nd?.usable ?: 0.0
                val bd = ctx.bare[x.id]?.value ?: x.exposure.bareDays?.usable ?: 0.0
                TableRow(CompareLogic.shortName(x) + if (x.isBaseline) " (today)" else "", x.id == s.id,
                    "${afv(nd?.value)} (${afv(nd?.low)}–${afv(nd?.high)})${if (Regex("safflower|wheat", RegexOption.IGNORE_CASE).containsMatchIn(x.name)) "*" else ""}",
                    if ((nd?.low ?: v) / 304.8 > limit) "over" else if ((nd?.high ?: v) / 304.8 <= limit) "fits" else "may go over",
                    "${bd.roundToInt()}${if (x.isBaseline && ctx.bare[x.id] != null) " seen" else " est."}", ctx.heat[x.id]?.let { Fmt.one(it.value) } ?: "–")
            },
            checks = checks,
            sources = "NASA: Landsat (NASA/USGS) for the field calendar with Sentinel-2 (ESA), cross-checked with HLS; NASA POWER sun, wind and humidity for crop water use; NASADEM for slope. Outlooks: NOAA Climate Prediction Center, US Drought Monitor, CDEC reservoir reports. Weather: NOAA stations. Soil: USDA soil survey (SSURGO). ${SeasonCalc.BARE_DEF} ${CompareLogic.HEAT_NOTE}",
        )
    }
}
