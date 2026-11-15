package app.croplytics.domain

import app.croplytics.data.remote.dto.SourcedNumberDto
import app.croplytics.data.remote.dto.StrategyDto
import kotlin.math.abs
import kotlin.math.roundToInt

enum class LimitFit { Fits, MayGoOver, Over, Unknown }

data class Range(val value: Double, val low: Double, val high: Double)

/** One line of gain or give-up, in acre-feet or days. */
data class Change(val title: String, val amount: String)

data class OptionComparison(
    val id: String,
    val name: String,
    val fullName: String,
    val need: Range?,
    val fit: LimitFit,
    val gains: List<Change>,
    val giveUps: List<Change>,
    /** Ranges overlap: inputs are not precise enough to say which is better. */
    val unclear: List<String>,
    val rank: Int?,
)

data class TodayRotation(val id: String, val name: String, val need: Range?, val fit: LimitFit, val bareDays: Double?)

data class CompareSummary(
    val today: TodayRotation,
    /** The top two alternatives by the rotation model's score. */
    val top: List<OptionComparison>,
    /** Every alternative, best first, for "See all options". */
    val all: List<OptionComparison>,
    val openetLine: String,
    val tieNote: String?,
)

object CompareBuilder {
    /** Short rotation names the grower reads at a glance (same as the web app). */
    private val short = mapOf(
        "car0_rice_winterflood" to "Rice + winter flood", "car1_rice_wintercover" to "Rice + winter cover",
        "car2_dryyear_safflower" to "Dry-year safflower", "car3_rice_wheat" to "Rice – wheat",
        "caf0_alfalfa" to "Alfalfa stand", "caf1_smallgrain_corn" to "Small grain + corn",
        "caf2_smallgrain_sorghumsudan" to "Small grain + sorghum-sudan", "caf3_alfalfa_break" to "Short alfalfa + break",
    )

    fun shortName(id: String, name: String): String =
        short[id] ?: short.entries.firstOrNull { id.endsWith(it.key.substringAfter('_')) }?.value
            ?: name.split(',', '(').first().trim()

    private fun range(n: SourcedNumberDto?): Range? {
        val v = n?.usable ?: return null
        return Range(v, n.low ?: v, n.high ?: v)
    }

    private fun need(s: StrategyDto): Range? =
        range(s.water.irrigationNeedAfAc) ?: range(s.water.irrigationNeedMm)?.let {
            Range(Units.mmToAfAc(it.value), Units.mmToAfAc(it.low), Units.mmToAfAc(it.high))
        }

    fun fit(need: Range?, limit: Double?): LimitFit = when {
        need == null || limit == null -> LimitFit.Unknown
        need.high <= limit -> LimitFit.Fits
        need.low > limit -> LimitFit.Over
        else -> LimitFit.MayGoOver
    }

    private enum class Verdict { Better, Worse, Unclear, Same, None }

    /** Lower is better for every metric here. Better/worse only when the likely ranges do not overlap. */
    private fun verdict(alt: Range?, today: Range?): Verdict {
        if (alt == null || today == null) return Verdict.None
        if (alt == today) return Verdict.Same
        if (alt.high < today.low) return Verdict.Better
        if (alt.low > today.high) return Verdict.Worse
        if (alt.low == alt.high && today.low == today.high) return if (alt.value < today.value) Verdict.Better else if (alt.value > today.value) Verdict.Worse else Verdict.Same
        return Verdict.Unclear
    }

    private fun days(v: Double) = if (v < 10) Fmt.one(v) else v.roundToInt().toString()

    fun build(strategies: List<StrategyDto>, limit: Double?, acres: Int?): CompareSummary? {
        val today = strategies.firstOrNull { it.isBaseline } ?: strategies.firstOrNull() ?: return null
        val todayNeed = need(today)
        val todayBare = range(today.exposure.bareDays)
        val todayRain = range(today.exposure.exposedRainDays)

        val alts = strategies.filter { it.id != today.id }
            .sortedWith(compareByDescending<StrategyDto> { it.composite.value ?: Double.NEGATIVE_INFINITY }.thenBy { it.composite.rank ?: Int.MAX_VALUE })
            .map { alt ->
                val gains = mutableListOf<Change>()
                val gives = mutableListOf<Change>()
                val unclear = mutableListOf<String>()
                val altNeed = need(alt)
                when (verdict(altNeed, todayNeed)) {
                    Verdict.Better, Verdict.Worse -> {
                        val d = altNeed!!.value - todayNeed!!.value
                        val total = acres?.let { " (${Fmt.whole(abs(d) * it)} acre-feet across $it acres)" } ?: ""
                        val change = Change(
                            if (d < 0) "Needs less irrigation water" else "Needs more irrigation water",
                            "about ${Fmt.absOne(d)} acre-ft/acre ${if (d < 0) "less" else "more"} a year$total",
                        )
                        if (d < 0) gains += change else gives += change
                    }
                    Verdict.Unclear -> unclear += "irrigation water"
                    else -> Unit
                }
                val altBare = range(alt.exposure.bareDays)
                when (verdict(altBare, todayBare)) {
                    Verdict.Better, Verdict.Worse -> {
                        val d = altBare!!.value - todayBare!!.value
                        val change = Change(if (d < 0) "Field bare fewer days" else "Field bare more days", "about ${days(abs(d))} ${if (d < 0) "fewer" else "more"} days a year")
                        if (d < 0) gains += change else gives += change
                    }
                    Verdict.Unclear -> unclear += "days the field sits bare"
                    else -> Unit
                }
                val altRain = range(alt.exposure.exposedRainDays)
                when (verdict(altRain, todayRain)) {
                    Verdict.Better, Verdict.Worse -> {
                        val d = altRain!!.value - todayRain!!.value
                        val change = Change(
                            if (d < 0) "Less heavy rain on bare soil" else "More heavy rain on bare soil",
                            "about ${days(abs(d))} ${if (d < 0) "fewer" else "more"} heavy-rain days a year on bare ground",
                        )
                        if (d < 0) gains += change else gives += change
                    }
                    Verdict.Unclear -> unclear += "heavy rain on bare soil"
                    else -> Unit
                }
                OptionComparison(
                    id = alt.id, name = shortName(alt.id, alt.name), fullName = alt.name, need = altNeed,
                    fit = fit(altNeed, limit), gains = gains, giveUps = gives, unclear = unclear, rank = alt.composite.rank,
                )
            }

        val openet = today.water.etcVsOpenetPct?.usable?.let { v ->
            "Checked against OpenET satellite measurements of this field: our estimate runs about ${abs(v).roundToInt()}% ${if (v >= 0) "high" else "low"}" +
                (if (v >= 0) ", as expected for a fully watered crop." else ".")
        } ?: "Not yet checked against measured water use (OpenET)."

        return CompareSummary(
            today = TodayRotation(today.id, shortName(today.id, today.name), todayNeed, fit(todayNeed, limit), todayBare?.value),
            top = alts.take(2),
            all = alts,
            openetLine = openet,
            tieNote = strategies.firstNotNullOfOrNull { it.composite.tieNote?.takeIf(String::isNotBlank) },
        )
    }
}
