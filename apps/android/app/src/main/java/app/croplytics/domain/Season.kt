package app.croplytics.domain

import kotlin.math.roundToInt

/**
 * Grower-unit summaries from the daily record and the satellite calendar, ported from the web app's season.ts and bare.ts.
 * Every result says which season it describes and how "normal" was built.
 */
object SeasonCalc {
    /** Heat threshold everywhere in the app: NOAA station highs of 104 °F (40 °C). */
    const val HOT_C = 40.0
    const val HOT_F = 104
    const val BARE_DEF = "Bare = satellite greenness below 0.2 and not under water."

    /** A view of the daily record restricted to days where [f] has a value. */
    class View(val dates: List<String>, val idx: IntArray) {
        val first get() = dates[idx.first()]
        val last get() = dates[idx.last()]
    }

    private fun only(d: Daily, f: (Int) -> Double?): View? {
        val idx = d.dates.indices.filter { f(it) != null }.toIntArray()
        return if (idx.isEmpty()) null else View(d.dates, idx)
    }

    private fun sumWhere(v: View, from: String, to: String, f: (Int) -> Double?): Pair<Double, Int> {
        var s = 0.0; var n = 0
        for (i in v.idx) { val dt = v.dates[i]; if (dt < from || dt > to) continue; val x = f(i); if (x != null) { s += x; n++ } }
        return s to n
    }

    data class Period(val label: String, val from: String, val to: String, val current: Boolean)

    private fun wyStart(iso: String) = iso.take(4).toInt().let { y -> if (iso.substring(5, 7).toInt() >= 10) y else y - 1 }

    /** The period "so far" for step t, or the last complete one if the record stops before it. */
    private fun periodFor(v: View, t: Int, water: Boolean): Period {
        val cut = Timeline.cutoffOf(t)
        val startY = if (water) wyStart(cut) else cut.take(4).toInt()
        val from = if (water) "$startY-10-01" else "$startY-01-01"
        if (v.last >= cut && v.first <= from) return Period(if (water) "since 1 Oct $startY" else "since 1 Jan $startY", from, cut, true)
        if (v.last >= from && v.first <= from) return Period("${if (water) "1 Oct $startY" else "1 Jan $startY"} to ${Timeline.fmtShort(v.last)}", from, v.last, true)
        val lastY = v.last.take(4).toInt()
        return if (water) {
            val e = if (v.last.substring(5) >= "09-30") lastY else lastY - 1
            Period("last season, Oct ${e - 1} to Sep $e", "${e - 1}-10-01", "$e-09-30", false)
        } else {
            val e = if (v.last.substring(5) >= "12-31") lastY else lastY - 1
            Period("last year, $e", "$e-01-01", "$e-12-31", false)
        }
    }

    private data class Normal(val mean: Double?, val n: Int)

    /** The same window in every earlier season with full data. */
    private fun normalOf(v: View, p: Period, f: (Int) -> Double?, count: Boolean = false): Normal {
        val y0 = p.from.take(4).toInt(); val vals = mutableListOf<Double>()
        for (k in 1..30) {
            val from = "${y0 - k}${p.from.drop(4)}"; val to = "${p.to.take(4).toInt() - k}${p.to.drop(4)}"
            if (from < v.first || to > v.last) continue
            val (s, n) = sumWhere(v, from, to, f)
            if (n > 0) vals += if (count) n.toDouble() else s
        }
        return Normal(vals.takeIf { it.isNotEmpty() }?.average(), vals.size)
    }

    private fun seasonsIn(v: View, p: Period): Int {
        var seasons = 0; val y0 = p.from.take(4).toInt()
        for (k in 1..30) { val from = "${y0 - k}${p.from.drop(4)}"; val to = "${p.to.take(4).toInt() - k}${p.to.drop(4)}"; if (from >= v.first && to <= v.last) seasons++ }
        return seasons
    }

    data class RainSoFar(val period: Period, val inches: Double, val normal: Double?, val nSeasons: Int, val pct: Double?, val imerg: Boolean)

    /** Rain so far this season: NASA GPM IMERG over the field, normal = the same dates in earlier seasons; NOAA stations as fallback. */
    fun rainSoFar(d: Daily, t: Int): RainSoFar? {
        val im = only(d) { d.imerg[it] }
        val v = im ?: only(d) { d.stPrecip[it] } ?: return null
        val f: (Int) -> Double? = { if (im != null) d.imerg[it] else d.stPrecip[it] }
        val p = periodFor(v, t, water = true)
        val (s, _) = sumWhere(v, p.from, p.to, f)
        val nm = normalOf(v, p, f)
        val inches = s / 25.4; val normal = nm.mean?.let { it / 25.4 }
        return RainSoFar(p, inches, normal, nm.n, normal?.takeIf { it > 0 }?.let { inches / it * 100 }, im != null)
    }

    data class HeatFrost(val period: Period, val hot: Int, val hotNormal: Double?, val frost: Int, val frostNormal: Double?, val frostPeriod: Period)

    fun heatFrost(d: Daily, t: Int): HeatFrost? {
        val v = only(d) { d.stTmax[it] } ?: return null
        val p = periodFor(v, t, water = false); val pf = periodFor(v, t, water = true)
        val hotF: (Int) -> Double? = { i -> d.stTmax[i]?.takeIf { it >= HOT_C }?.let { 1.0 } }
        val frostF: (Int) -> Double? = { i -> d.stTmin[i]?.takeIf { it * 9 / 5 + 32 <= 32 }?.let { 1.0 } }
        val hot = sumWhere(v, p.from, p.to, hotF).second; val frost = sumWhere(v, pf.from, pf.to, frostF).second
        fun zeroFill(m: Normal, per: Period): Double? { val s = seasonsIn(v, per); return if (s > 0) (m.mean ?: 0.0) * m.n / s else null }
        return HeatFrost(p, hot, zeroFill(normalOf(v, p, hotF, true), p), frost, zeroFill(normalOf(v, pf, frostF, true), pf), pf)
    }

    data class CropWater(val period: Period, val inches: Double, val normal: Double, val pct: Double?)

    /** Crop water use so far for today's rotation: the model's monthly use scaled by how thirsty this year's air was (NASA POWER). */
    fun cropWaterSoFar(d: Daily, etcByMonthMm: List<Double>, t: Int): CropWater? {
        val v = only(d) { d.eto[it] } ?: return null
        if (etcByMonthMm.size < 12) return null
        val p = periodFor(v, t, water = false)
        val endM = p.to.substring(5, 7).toInt(); val endD = p.to.substring(8, 10).toInt(); val y = p.from.take(4).toInt()
        var model = 0.0; var normal = 0.0
        for (m in 1..endM) {
            val lastDay = if (m < endM) Timeline.monthEnd(m, y) else endD
            val share = if (m < endM) 1.0 else endD.toDouble() / Timeline.monthEnd(m, y)
            fun sum(yy: Int) = sumWhere(v, "%04d-%02d-01".format(yy, m), "%04d-%02d-%02d".format(yy, m, lastDay)) { d.eto[it] }.first
            val thisY = sum(y)
            val others = (1..30).map { y - it }.takeWhile { "%04d-%02d-01".format(it, m) >= v.first }.map(::sum)
            val avg = if (others.isNotEmpty()) others.average() else thisY
            val etc = etcByMonthMm[m - 1] * share
            normal += etc
            model += if (avg > 0) etc * (thisY / avg) else etc
        }
        return CropWater(p, model / 25.4, normal / 25.4, if (normal > 0) model / normal * 100 else null)
    }

    /** Hot days (station high >= 104 °F) while a rotation leaves the field bare, per year on average. */
    fun hotBareDays(d: Daily, monthCover: String): Range? {
        val v = only(d) { d.stTmax[it] } ?: return null
        val y0 = v.first.take(4).toInt(); val y1 = v.last.take(4).toInt() - if (v.last.substring(5) >= "12-31") 0 else 1
        val per = mutableListOf<Double>()
        for (y in y0..y1) {
            var n = 0; var seen = 0; val ys = "$y"
            for (i in v.idx) {
                val dt = v.dates[i]; if (!dt.startsWith(ys)) continue
                val tx = d.stTmax[i] ?: continue
                seen++
                if (tx >= HOT_C && monthCover.getOrNull(dt.substring(5, 7).toInt() - 1) == 'b') n++
            }
            if (seen > 300) per += n.toDouble()
        }
        if (per.isEmpty()) return null
        return Range(per.average(), per.min(), per.max())
    }

    // ---------------- bare.ts ----------------

    /** Bare days in one year, scaled up for steps with no clear view. Null when under half the year was seen. */
    fun bareDaysYear(y: CalYear): Int? {
        val clear = y.rule.count { it != 'u' }
        if (clear < 18) return null
        return (y.rule.count { it == 'b' }.toDouble() / clear * 365).roundToInt()
    }

    data class ObservedBare(val value: Int, val years: List<Int>, val per: Map<Int, Int>)

    /** Satellite-seen bare days a year for the field's own rotation: the last 3 processed years. */
    fun observedBare(cal: FieldCalendar?): ObservedBare? {
        cal ?: return null
        val last = Timeline.yearOf(Calendars.lastDataT(cal))
        val per = cal.years.filter { it.year > last - 3 && it.year <= last }.mapNotNull { y -> bareDaysYear(y)?.let { y.year to it } }.toMap()
        if (per.isEmpty()) return null
        return ObservedBare(per.values.average().roundToInt(), per.keys.toList(), per)
    }

    /** When the field is usually bare: months bare in at least half of the recent clear years. */
    fun usuallyBareMonths(cal: FieldCalendar?): String {
        cal ?: return ""
        val last = Timeline.yearOf(Calendars.lastDataT(cal))
        val ys = cal.years.filter { it.year > last - 3 && it.year <= last }
        val months = (0 until 12).map { m ->
            var b = 0; var n = 0
            for (y in ys) for (k in 0 until 3) { val c = y.rule[m * 3 + k]; if (c != 'u') { n++; if (c == 'b') b++ } }
            n > 0 && b.toDouble() / n >= 0.5
        }
        if (months.none { it }) return "rarely bare"
        val runs = mutableListOf<Pair<Int, Int>>()
        for (m in 0 until 12) if (months[m] && !months[(m + 11) % 12]) { var e = m; while (months[(e + 1) % 12] && (e + 1) % 12 != m) e = (e + 1) % 12; runs += m to e }
        if (runs.isEmpty()) return "bare all year"
        return runs.joinToString(" and ") { (a, e) -> if (a == e) Timeline.MONTHS[a] else "${Timeline.MONTHS[a]} to ${Timeline.MONTHS[e]}" }
    }

    /** This winter's usual bare window from the satellite calendar, and how often a 1-inch rain day landed in it. */
    data class BareWindow(val from: String, val to: String, val days: Int, val chance: Double?, val winters: Int, val hits: Int)

    fun fmtIn(v: Double) = if (v < 10) Fmt.one(v) else v.roundToInt().toString()
}
