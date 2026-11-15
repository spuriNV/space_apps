package app.croplytics.domain

import app.croplytics.data.remote.dto.SourcedNumberDto
import app.croplytics.data.remote.dto.StrategyDto
import kotlin.math.abs
import kotlin.math.roundToInt

/** A value with its likely range. */
data class Range(val value: Double, val low: Double, val high: Double)

/** Ported from the web app's ComparePanel.tsx and api.ts normStrategy: gain / give up vs today, in acre-feet, days and rules of thumb. */
object CompareLogic {
    enum class Weather(val label: String) { Typical("Typical year"), Dry("Dry, like 2022"), Wet("Wet, like 2023") }
    enum class Verdict { Better, Worse, Unclear, Same, None }
    enum class Unit { AF, DAYS, SCORE }

    private val SHORT = mapOf(
        "car0_rice_winterflood" to "Rice + winter flood", "car1_rice_wintercover" to "Rice + winter cover", "car2_dryyear_safflower" to "Dry-year safflower",
        "car3_rice_wheat" to "Rice – wheat", "caf0_alfalfa" to "Alfalfa stand", "caf1_smallgrain_corn" to "Small grain + corn",
        "caf2_smallgrain_sorghumsudan" to "Small grain + sorghum-sudan", "caf3_alfalfa_break" to "Short alfalfa + break",
    )
    /** Short rotation names; new fields reuse their family's rotation ids with another prefix. */
    fun shortName(s: StrategyDto): String = SHORT[s.id] ?: SHORT.entries.firstOrNull { s.id.endsWith(it.key.substringAfter('_')) }?.value ?: s.name.split(',', '(').first().trim()

    private val CROP_LABEL = mapOf(
        "open_water_flood" to "flood", "rice_medium_grain" to "rice", "cereal_vetch_cover" to "cereal + vetch cover", "safflower" to "safflower",
        "winter_wheat" to "winter wheat", "alfalfa_hay" to "alfalfa", "small_grain_silage" to "small-grain silage", "silage_corn" to "silage corn", "sorghum_sudan" to "sorghum-sudan",
    )
    private fun md(s: String?): Double { val p = s.orEmpty().split("-").mapNotNull { it.toIntOrNull() }; return if (p.size == 2) p[0] + (p[1] - 1) / 31.0 else 0.0 }

    /** Month by month: what is in the field (words) and its cover class (b p c w), for the strip under each option. */
    data class MonthStrip(val months: List<String>, val cover: String)
    fun monthStrip(s: StrategyDto): MonthStrip {
        val year = if (s.id.endsWith("alfalfa_break")) 3 else 1
        val months = mutableListOf<String>(); val cover = StringBuilder()
        for (m in 1..12) {
            val x = m + 0.5
            val hit = s.calendar.filter { it.year == year }.firstOrNull { c -> val a = md(c.plant); val b = md(c.harvest); if (a == b) true else if (a < b) x >= a && x < b else x >= a || x < b }
            months += hit?.let { CROP_LABEL[it.cropId] ?: it.cropId.replace('_', ' ') } ?: "bare"
            cover.append(when { hit == null -> 'b'; hit.role == "water" -> 'w'; hit.role == "establishing" || (abs(x - md(hit.plant)) < 1 && md(hit.plant) != md(hit.harvest)) -> 'p'; else -> 'c' })
        }
        return MonthStrip(months, cover.toString())
    }

    private fun n(x: SourcedNumberDto?): Range? = x?.usable?.let { Range(it, x.low ?: it, x.high ?: it) }
    private fun af(r: Range?) = r?.let { Range(it.value / 304.8, it.low / 304.8, it.high / 304.8) }
    private fun replay(s: StrategyDto, w: Weather) = when (w) { Weather.Typical -> null; Weather.Dry -> s.exposure.replay["2022"]; Weather.Wet -> s.exposure.replay["2023"] }

    fun water(s: StrategyDto, w: Weather): Range? = af(n(replay(s, w)?.irrigationNeedMm ?: s.water.irrigationNeedMm))

    /** Hot days on bare soil per rotation (NOAA station highs) and bare days (satellite-seen for today, model for the others). */
    data class Ctx(val heat: Map<String, Range>, val bare: Map<String, Range>, val bareYears: List<Int>)
    fun ctx(strategies: List<StrategyDto>, daily: Daily?, cal: FieldCalendar?): Ctx {
        val heat = if (daily != null) strategies.mapNotNull { s -> SeasonCalc.hotBareDays(daily, monthStrip(s).cover)?.let { s.id to Range(it.value, it.value, it.value) } }.toMap() else emptyMap()
        val ob = SeasonCalc.observedBare(cal); val today = strategies.firstOrNull { it.isBaseline }
        val bare = if (ob != null && today != null) mapOf(today.id to Range(ob.value.toDouble(), ob.value.toDouble(), ob.value.toDouble())) else emptyMap()
        return Ctx(heat, bare, ob?.years.orEmpty())
    }

    data class Metric(val key: String, val label: String, val unit: Unit, val higherIsBetter: Boolean, val gain: String, val loss: String, val get: (StrategyDto, Weather, Ctx) -> Range?)

    val UNIT_METRICS = listOf(
        Metric("water", "Irrigation water needed", Unit.AF, false, "Needs less irrigation water", "Needs more irrigation water") { s, w, _ -> water(s, w) },
        Metric("bare", "Days the field sits bare", Unit.DAYS, false, "Field bare fewer days", "Field bare more days") { s, _, c -> c.bare[s.id] ?: n(s.exposure.bareDays) },
        Metric("rain", "Heavy rain on bare soil", Unit.DAYS, false, "Less heavy rain on bare soil", "More heavy rain on bare soil") { s, w, _ -> n(replay(s, w)?.exposedRainDays ?: s.exposure.exposedRainDays) },
        Metric("heat", "Hot days on bare soil (104 °F or more)", Unit.DAYS, false, "Fewer hot days on bare soil", "More hot days on bare soil") { s, _, c -> c.heat[s.id] },
    )
    private val PLAIN = listOf(
        listOf("forage_value", "Feed you can cut or graze", "More feed to cut or graze", "Less feed to cut or graze"),
        listOf("n_fixation", "Adds nitrogen (legumes)", "Adds more nitrogen", "Adds less nitrogen"),
        listOf("erosion", "Protects soil from washing away", "Better soil protection", "Less soil protection"),
        listOf("organic_matter", "Builds organic matter", "Builds more organic matter", "Builds less organic matter"),
        listOf("market", "Crops you can sell locally", "Easier to sell", "Harder to sell"),
        listOf("pest_break", "Breaks pest cycles", "Breaks pest cycles better", "Breaks pest cycles less"),
        listOf("infiltration", "Water soaks in", "Water soaks in better", "Water soaks in less"),
        listOf("n_scavenging", "Holds nitrogen over winter", "Holds more nitrogen over winter", "Holds less nitrogen over winter"),
    )
    val SCORE_METRICS = PLAIN.map { (k, label, gain, loss) -> Metric(k, label, Unit.SCORE, true, gain, loss) { s, _, _ -> n(s.scores[k]) } }

    /** Scores the same for every rotation carry no information. */
    fun constantScores(ss: List<StrategyDto>): Set<String> = SCORE_METRICS.filter { m -> val v = ss.map { it.scores[m.key]?.usable }; v.all { it == null || it == v[0] } }.map { it.key }.toSet()

    fun verdict(a: Range?, b: Range?, hib: Boolean): Verdict {
        if (a == null || b == null) return Verdict.None
        if (a.low == b.low && a.high == b.high && a.value == b.value) return Verdict.Same
        if (a.low > b.high) return if (hib) Verdict.Better else Verdict.Worse
        if (a.high < b.low) return if (hib) Verdict.Worse else Verdict.Better
        if (a.low == a.high && b.low == b.high) return if ((a.value > b.value) == hib) Verdict.Better else Verdict.Worse
        return Verdict.Unclear
    }

    private fun r1(x: Double) = if (abs(x) < 10) Fmt.one(x) else String.format(java.util.Locale.US, "%,d", x.roundToInt())
    fun fmt(m: Metric, x: Range?) = when { x == null -> "not scored yet"; m.unit == Unit.AF -> "${Fmt.one(x.value)} acre-ft/acre"; m.unit == Unit.DAYS -> "${r1(x.value)} days a year"; else -> "${x.value.roundToInt()} of 100" }
    fun rng(m: Metric, x: Range?): String {
        x ?: return ""
        val tol = if (m.unit == Unit.AF) 0.05 else 0.5
        if (abs(x.high - x.low) <= tol) return ""
        return if (m.unit == Unit.AF) "likely ${Fmt.one(x.low)}–${Fmt.one(x.high)}" else "likely ${x.low.roundToInt()}–${x.high.roundToInt()}"
    }
    fun delta(m: Metric, a: Double, b: Double): String {
        val d = abs(a - b)
        return when (m.unit) {
            Unit.AF -> "about ${Fmt.one(d)} acre-ft/acre ${if (a < b) "less" else "more"} a year (${(d * 12).roundToInt()} in)"
            Unit.DAYS -> "about ${r1(d)} ${if (a < b) "fewer" else "more"} days a year"
            Unit.SCORE -> "${a.roundToInt()} vs ${b.roundToInt()} on a 0–100 rule of thumb"
        }
    }

    data class Row(val m: Metric, val a: Range?, val b: Range?, val v: Verdict)

    fun rows(alt: StrategyDto, today: StrategyDto, weather: Weather, ctx: Ctx, all: List<StrategyDto>, detail: Boolean, heavySoil: Boolean): List<Row> {
        val flat = constantScores(all)
        val metrics = if (detail) UNIT_METRICS + SCORE_METRICS.filter { it.key !in flat }.map { label(it, heavySoil) } else UNIT_METRICS
        return metrics.map { m -> val a = m.get(alt, weather, ctx); val b = m.get(today, weather, ctx); Row(m, a, b, verdict(a, b, m.higherIsBetter)) }
    }

    fun allRows(today: StrategyDto, weather: Weather, ctx: Ctx, all: List<StrategyDto>, heavySoil: Boolean): List<Metric> =
        UNIT_METRICS + SCORE_METRICS.filter { it.key !in constantScores(all) }.map { label(it, heavySoil) }

    private fun label(m: Metric, heavy: Boolean) = if (m.key == "infiltration" && heavy) m.copy(gain = "${m.gain} (small effect on this heavy, slow-draining soil)", loss = "${m.loss} (small effect on this heavy soil)") else m

    fun fits(s: StrategyDto, w: Weather, limit: Double): String {
        if (BcLogic.rainFed(s)) return "Fits your limit"
        val r = water(s, w) ?: return "No water estimate"
        return if (r.high <= limit) "Fits your limit" else if (r.low > limit) "Over your limit" else "May go over your limit"
    }

    /** Priorities (0 not at all .. 4 top priority) and the rain / heat what-ifs, re-scored by the rotation model (POST /score). */
    val PRIORITIES = listOf("water_use" to "Saving water", "forage_value" to "Feed to cut or graze", "n_fixation" to "Adding nitrogen", "erosion" to "Keeping soil in place", "organic_matter" to "Building organic matter", "pest_break" to "Breaking pest cycles")
    val LEVEL = listOf("Not at all", "Normal", "More", "Much more", "Top priority")
    val RAIN = listOf(-20.0 to "20% less rain", 0.0 to "Normal rain", 20.0 to "20% more rain")
    val HEAT = listOf(0.0 to "Normal heat", 2.0 to "4 °F warmer", 4.0 to "7 °F warmer")
    fun defaultWeight(k: String) = if (k == "pest_break") 0 else 1
    fun requestWeights(w: Map<String, Int>): Map<String, Double> = (PRIORITIES.associate { (k, _) -> k to defaultWeight(k).toDouble() } + ("market" to 0.0) + w.mapValues { it.value.toDouble() })

    /** Plain gain / give-up lines for the adviser summary (typical year). */
    data class Tradeoffs(val gains: List<String>, val losses: List<String>, val unclear: List<String>)
    fun tradeoffs(today: StrategyDto, alt: StrategyDto, ctx: Ctx, all: List<StrategyDto>, heavySoil: Boolean): Tradeoffs {
        val flat = constantScores(all)
        val rows = (UNIT_METRICS + SCORE_METRICS.filter { it.key !in flat }).map { m -> val a = m.get(alt, Weather.Typical, ctx); val b = m.get(today, Weather.Typical, ctx); Row(m, a, b, verdict(a, b, m.higherIsBetter)) }
        fun line(r: Row, gain: Boolean) = if (r.m.unit == Unit.SCORE) "${if (gain) r.m.gain else r.m.loss} (rule of thumb${if (r.m.key == "infiltration" && heavySoil) "; small effect on this heavy soil" else ""})." else "${if (gain) r.m.gain else r.m.loss}: ${delta(r.m, r.a!!.value, r.b!!.value)}."
        return Tradeoffs(rows.filter { it.v == Verdict.Better }.map { line(it, true) }, rows.filter { it.v == Verdict.Worse }.map { line(it, false) }, rows.filter { it.v == Verdict.Unclear || it.v == Verdict.Same }.map { it.m.label.lowercase() })
    }

    /** Water text for a rotation: "Rain-fed (no irrigation)" or "1.9 acre-ft/acre". */
    fun needText(s: StrategyDto, w: Weather) = if (BcLogic.rainFed(s)) BcLogic.RAIN_FED else "${Fmt.one(water(s, w)?.value ?: 0.0)} acre-ft/acre"

    const val HEAT_NOTE = "Hot days = NOAA weather-station highs of 104 °F or more, in months the rotation leaves the field bare."
}
