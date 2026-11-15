package app.croplytics.domain

import java.time.LocalDate
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * The app's clock, ported from the web app's lib.ts: time is counted in 10-day steps ("t"), 36 per year
 * from 2016. Step k of a year is early/mid/late of month k / 3.
 */
object Timeline {
    const val FIRST_YEAR = 2016
    /** By default calendars show this season plus the last 3; older years sit behind "Show earlier years". */
    const val RECENT_FROM = 2023
    val MONTHS = listOf("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    val MONTHS_FULL = listOf("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
    private val PART = listOf("Early", "Mid", "Late")

    fun tOf(year: Int, step: Int) = (year - FIRST_YEAR) * 36 + step
    fun yearOf(t: Int) = FIRST_YEAR + Math.floorDiv(t, 36)
    fun stepOf(t: Int) = Math.floorMod(t, 36)
    fun stepOf(d: LocalDate) = (d.monthValue - 1) * 3 + when { d.dayOfMonth <= 10 -> 0; d.dayOfMonth <= 20 -> 1; else -> 2 }
    fun todayT(today: LocalDate) = tOf(today.year, stepOf(today))
    fun years(today: LocalDate) = (FIRST_YEAR..today.year).toList()
    fun tMax(today: LocalDate) = years(today).size * 36 - 1

    /** "Mid Nov 2026". */
    fun label(t: Int): String { val d = stepOf(t); return "${PART[d % 3]} ${MONTHS[d / 3]} ${yearOf(t)}" }
    /** "mid Nov 2026". */
    fun when_(t: Int): String = label(t).replaceFirstChar { it.lowercase() }
    /** "early November" without the year. */
    fun stepWords(step: Int) = "${PART[step % 3].lowercase()} ${MONTHS_FULL[step / 3]}"
    fun stepShort(step: Int) = "${PART[step % 3].lowercase()} ${MONTHS[step / 3]}"

    fun dateToT(iso: String): Int {
        val p = iso.take(10).split("-").map { it.toInt() }
        return tOf(p[0], (p[1] - 1) * 3 + when { p[2] <= 10 -> 0; p[2] <= 20 -> 1; else -> 2 })
    }

    /** "14 Nov 2026". */
    fun fmtDate(iso: String?): String {
        val p = iso?.take(10)?.split("-")?.mapNotNull { it.toIntOrNull() } ?: return ""
        return if (p.size == 3) "${p[2]} ${MONTHS[p[1] - 1]} ${p[0]}" else iso
    }
    /** "14 Nov". */
    fun fmtShort(iso: String?) = fmtDate(iso).replace(Regex(" \\d{4}$"), "")

    private val MONTH_END = intArrayOf(31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    fun monthEnd(month1: Int, year: Int) = MONTH_END[month1 - 1] + if (month1 == 2 && year % 4 == 0) 1 else 0

    /** Last day covered by step t, as YYYY-MM-DD. */
    fun cutoffOf(t: Int): String {
        val y = yearOf(t); val d = stepOf(t); val m = d / 3
        val day = when (d % 3) { 0 -> 10; 1 -> 20; else -> monthEnd(m + 1, y) }
        return "%04d-%02d-%02d".format(y, m + 1, day)
    }
}

/** Satellite cover classes, as the web app's one-letter codes. */
object Cls {
    const val BARE = 'b'; const val PARTIAL = 'p'; const val COVERED = 'c'; const val WATER = 'w'; const val UNKNOWN = 'u'
    val LABEL = mapOf('b' to "Bare", 'p' to "Partial cover", 'c' to "Covered", 'w' to "Water", 'u' to "Unknown (cloud)")
    /** Data colours (never chrome). */
    val COLOR = mapOf('b' to "#a8703f", 'p' to "#b7d77a", 'c' to "#2f9e4b", 'w' to "#3d97e8", 'u' to "#6b7280")
    fun of(raw: String?) = when (raw) { "bare" -> 'b'; "partial" -> 'p'; "covered" -> 'c'; "water" -> 'w'; else -> 'u' }
}

fun clamp(v: Double, a: Double, b: Double) = max(a, min(b, v))

/** Colour ramps (lib.ts), returning "#rrggbb" so the same value feeds Compose and MapLibre. */
object Ramps {
    val NDVI = listOf(0.35 to "#9fd45f", 0.6 to "#43b04f", 0.9 to "#12733a")
    val SMAP = listOf(0.0 to "#b0592a", 35.0 to "#d8b77a", 60.0 to "#a5d6cf", 100.0 to "#17a89c")
    val GRACE = listOf(0.0 to "#8e2148", 30.0 to "#c9688a", 60.0 to "#9a9fd8", 100.0 to "#39c4d8")

    private fun rgb(hex: String) = hex.removePrefix("#").toLong(16).let { intArrayOf(((it shr 16) and 255).toInt(), ((it shr 8) and 255).toInt(), (it and 255).toInt()) }

    fun ramp(stops: List<Pair<Double, String>>, v: Double): String {
        val x = clamp(v, stops.first().first, stops.last().first)
        for (i in 1 until stops.size) {
            if (x <= stops[i].first) {
                val (a, ca) = stops[i - 1]; val (b, cb) = stops[i]
                val f = (x - a) / ((b - a).takeIf { it != 0.0 } ?: 1.0)
                val A = rgb(ca); val B = rgb(cb)
                return "#%02x%02x%02x".format(*IntArray(3) { k -> (A[k] + (B[k] - A[k]) * f).roundToInt() }.toTypedArray())
            }
        }
        return stops.last().second
    }
}

fun ordinal(n: Int): String = Fmt.ordinal(n)
