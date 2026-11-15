package app.croplytics.domain

import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.abs
import kotlin.math.roundToInt

/** Grower units first: acres, inches, acre-feet per acre. */
object Units {
    const val ACRES_PER_HA = 2.4710538
    const val MM_PER_INCH = 25.4
    const val MM_PER_ACRE_FOOT_PER_ACRE = 304.8

    fun haToAcres(ha: Double) = ha * ACRES_PER_HA
    fun mmToInches(mm: Double) = mm / MM_PER_INCH
    fun mmToAfAc(mm: Double) = mm / MM_PER_ACRE_FOOT_PER_ACRE
}

object Fmt {
    private val dayMonthYear = DateTimeFormatter.ofPattern("d MMM yyyy", Locale.UK)
    private val dayMonth = DateTimeFormatter.ofPattern("d MMM", Locale.UK)
    private val monthNames = listOf("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    private val monthFull = listOf(
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    )

    fun one(v: Double): String = String.format(Locale.US, "%.1f", v)

    /** Rounded with thousands separators: 2,243,711. */
    fun whole(v: Double): String = String.format(Locale.US, "%,d", v.roundToInt())

    fun pct(v: Double): String = "${v.roundToInt()}%"

    /** 1st, 2nd, 3rd, 48th, 53rd. */
    fun ordinal(n: Int): String {
        val suffix = if (n % 100 in 11..13) "th" else when (n % 10) { 1 -> "st"; 2 -> "nd"; 3 -> "rd"; else -> "th" }
        return "$n$suffix"
    }

    /** "13 Nov 2026" from an ISO date (or its first 10 characters); the input itself if it does not parse. */
    fun date(iso: String?): String = parse(iso)?.format(dayMonthYear) ?: iso.orEmpty()

    fun dayMonth(iso: String?): String = parse(iso)?.format(dayMonth) ?: iso.orEmpty()

    fun date(d: LocalDate): String = d.format(dayMonthYear)

    /** "early Nov 2026" / "mid Sep 2026": grower terms, not dekads. */
    fun roughly(iso: String?): String {
        val d = parse(iso) ?: return iso.orEmpty()
        val part = when { d.dayOfMonth <= 10 -> "early"; d.dayOfMonth <= 20 -> "mid"; else -> "late" }
        return "$part ${monthNames[d.monthValue - 1]} ${d.year}"
    }

    /** "02-13" (MM-DD) to "mid February". */
    fun monthDayWords(mmdd: String?): String? {
        val parts = mmdd?.split("-")?.mapNotNull { it.toIntOrNull() } ?: return null
        if (parts.size != 2 || parts[0] !in 1..12) return null
        val part = when { parts[1] <= 10 -> "early"; parts[1] <= 20 -> "mid"; else -> "late" }
        return "$part ${monthFull[parts[0] - 1]}"
    }

    fun monthShort(month1: Int) = monthNames[(month1 - 1).mod(12)]

    fun parse(iso: String?): LocalDate? = iso?.takeIf { it.length >= 10 }?.let { runCatching { LocalDate.parse(it.substring(0, 10)) }.getOrNull() }

    /** "about 3.3 more" / "about 3.3 less" style helper for differences. */
    fun absOne(v: Double) = one(abs(v))

    /** Money in the grower's words: "$248 million", "$346 thousand". */
    fun usd(v: Double): String = when {
        v >= 1e6 -> "$${if (v >= 1e8) whole(v / 1e6) else one(v / 1e6)} million"
        else -> "$${whole(v / 1e3)} thousand"
    }
}
