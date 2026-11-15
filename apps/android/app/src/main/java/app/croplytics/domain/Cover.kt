package app.croplytics.domain

import app.croplytics.data.remote.dto.CalendarDto
import app.croplytics.data.remote.dto.CalendarYearDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.ObservationDto
import java.time.LocalDate

/** What the satellites saw on the field. Bare = greenness below 0.2 and not under water (one definition everywhere). */
enum class Cover { Bare, Partial, Covered, Water, Unknown;

    companion object {
        fun of(raw: String?): Cover = when (raw) {
            "bare" -> Bare
            "partial" -> Partial
            "covered" -> Covered
            "water" -> Water
            else -> Unknown
        }
    }
}

const val BARE_DEFINITION = "Bare = satellite greenness below 0.2 and not under water."

object CoverCalendar {
    /** 36 ten-day steps (early/mid/late each month) for one year, sampled on the 5th, 15th and 25th. */
    fun tenDaySteps(year: CalendarYearDto): List<Cover> = (0 until 36).map { k ->
        val date = LocalDate.of(year.year, k / 3 + 1, listOf(5, 15, 25)[k % 3])
        val doy = date.dayOfYear
        Cover.of(year.segments.firstOrNull { doy in it.startDoy..it.endDoy }?.cls)
    }

    /** Ten-day step index (0..35) of a date. */
    fun stepOf(date: LocalDate): Int = (date.monthValue - 1) * 3 + when { date.dayOfMonth <= 10 -> 0; date.dayOfMonth <= 20 -> 1; else -> 2 }

    /** The latest satellite view with a clear class and a greenness reading. */
    fun latestClear(cal: CalendarDto): ObservationDto? = cal.years.sortedBy { it.year }.asReversed().firstNotNullOfOrNull { y ->
        y.observations.lastOrNull { Cover.of(it.cls) != Cover.Unknown && it.ndvi != null }
    }

    /** Days per class over a set of years, for "Green about 140 days, bare 60". */
    fun daysByClass(year: CalendarYearDto): Map<Cover, Int> = tenDaySteps(year).groupingBy { it }.eachCount().mapValues { it.value * 10 }

    /** Plain words for a cover class at a date, with harvest context from the year's markers. */
    fun stateWords(cover: Cover, year: CalendarYearDto?, onDate: String?): String {
        val lastHarvest = year?.markers?.filter { it.type == "senescence_harvest" && (onDate == null || it.date <= onDate) }?.lastOrNull()
        val lastGreenUp = year?.markers?.filter { it.type == "green_up" && (onDate == null || it.date <= onDate) }?.lastOrNull()
        return when (cover) {
            Cover.Covered -> lastGreenUp?.let { "Crop growing, green since ${Fmt.roughly(it.date).substringBeforeLast(' ')}" } ?: "Crop growing, full green cover"
            Cover.Partial -> "Thin cover"
            Cover.Bare -> lastHarvest?.let { "Bare since harvest in ${Fmt.roughly(it.date).substringBeforeLast(' ')}" } ?: "Bare ground"
            Cover.Water -> "Under water"
            Cover.Unknown -> "No clear satellite view"
        }
    }
}

/** Water limit rules: the grower's own, else the example per field family (PLAN.md: Colusa 5.0, Kings 3.0). */
object WaterLimit {
    const val MIN = 0.5
    const val MAX = 8.0

    fun example(loc: LocationDto?, id: String): Double? =
        loc?.water?.allocationInput?.value ?: when {
            id.startsWith("car") -> 5.0
            id.startsWith("caf") -> 3.0
            else -> null
        }
}
