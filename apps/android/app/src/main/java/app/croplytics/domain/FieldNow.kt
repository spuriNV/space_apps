package app.croplytics.domain

import app.croplytics.data.remote.dto.CalendarDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.NasaNowDto
import app.croplytics.data.remote.dto.StrategyDto
import java.time.LocalDate
import kotlin.math.roundToInt

/** One question a grower would ask, with a plain answer, its number and one source line. */
data class Answer(
    val question: String,
    val headline: String,
    val detail: String,
    val cite: String,
    /** Glossary entries behind "What's this?", first match wins (ids differ between API versions). */
    val glossaryIds: List<String> = emptyList(),
    val warn: Boolean = false,
)

/** A reading drawn as a bar with a reference mark: value as a share of the track, mark = normal or limit. */
data class BarReading(
    val label: String,
    val value: String,
    val fill: Float,
    val mark: Float?,
    val markLabel: String?,
    val note: String,
    val warn: Boolean = false,
    /** Spoken by TalkBack instead of the drawing. */
    val spoken: String,
)

data class PercentileReading(val soil: Int?, val groundwater: Int?, val note: String, val spoken: String)

data class SeasonStrip(val year: Int, val steps: List<Cover>, val todayStep: Int, val state: String, val spoken: String)

data class FieldNowSummary(
    val strip: SeasonStrip?,
    val rain: BarReading?,
    val waterNeed: BarReading?,
    val greenness: BarReading?,
    val soil: PercentileReading?,
    /** At most four answers (PLAN.md "Farmer-first default"). */
    val answers: List<Answer>,
)

object FieldNowBuilder {
    private fun band(pct: Double, hi: String, mid: String, lo: String) = when { pct >= 67 -> hi; pct > 33 -> mid; else -> lo }
    private fun vsNormal(pct: Double, wet: String, dry: String) = when { pct >= 115 -> wet; pct <= 85 -> dry; else -> "about normal" }

    fun build(
        loc: LocationDto,
        calendar: CalendarDto?,
        nasaNow: NasaNowDto?,
        strategies: List<StrategyDto>?,
        limit: Double?,
        limitIsExample: Boolean,
        today: LocalDate,
    ): FieldNowSummary {
        val id = FieldNames.identity(loc)
        val hist = FieldNames.history(loc)
        val readings = nasaNow?.readings.orEmpty()

        // --- what is growing: the latest clear satellite view ---
        val latest = calendar?.let(CoverCalendar::latestClear)
        val latestYear = calendar?.years?.maxByOrNull { it.year }
        val latestCover = Cover.of(latest?.cls)
        val stateYear = calendar?.years?.firstOrNull { y -> latest != null && latest.date.startsWith(y.year.toString()) }
        val stateText = latest?.let { CoverCalendar.stateWords(latestCover, stateYear, it.date) }
        val strip = latestYear?.let { y ->
            val steps = CoverCalendar.tenDaySteps(y)
            val step = if (y.year == today.year) CoverCalendar.stepOf(today) else 35
            val counts = steps.groupingBy { it }.eachCount()
            SeasonStrip(
                year = y.year, steps = steps, todayStep = step, state = stateText ?: "No clear satellite view",
                spoken = "${y.year} so far: green about ${(counts[Cover.Covered] ?: 0) * 10} days, thin ${(counts[Cover.Partial] ?: 0) * 10}, " +
                    "bare ${(counts[Cover.Bare] ?: 0) * 10}, under water ${(counts[Cover.Water] ?: 0) * 10}. Now: ${stateText ?: "no clear view"}.",
            )
        }

        // --- rain since 1 Oct vs normal (NASA GPM IMERG) ---
        val rainMm = readings["imerg_wy_to_date_mm"]?.value
        val normalMm = readings["imerg_wy_to_date_normal_mm"]?.value
        val rainObs = readings["imerg_wy_to_date_mm"]?.obsDate
        val rainPct = if (rainMm != null && normalMm != null && normalMm > 0) rainMm / normalMm * 100 else null
        val rain = if (rainMm != null) {
            val inches = Units.mmToInches(rainMm)
            val normalIn = normalMm?.let(Units::mmToInches)
            val scale = maxOf(inches, normalIn ?: 0.0) * 1.25
            BarReading(
                label = "Rain since 1 Oct",
                value = "${Fmt.one(inches)} in",
                fill = if (scale > 0) (inches / scale).toFloat() else 0f,
                mark = normalIn?.let { if (scale > 0) (it / scale).toFloat() else null },
                markLabel = "normal",
                note = rainPct?.let { "${it.roundToInt()}% of normal" } ?: "",
                spoken = "Rain since 1 October: ${Fmt.one(inches)} inches" + (normalIn?.let { ", normal ${Fmt.one(it)} inches" } ?: ""),
            )
        } else null

        // --- irrigation need of today's rotation vs the water limit ---
        val base = strategies?.firstOrNull { it.isBaseline }
        val need = base?.water?.irrigationNeedAfAc
        val needV = need?.usable ?: base?.water?.irrigationNeedMm?.usable?.let(Units::mmToAfAc)
        val waterNeed = needV?.let { v ->
            val scale = maxOf(v, limit ?: 0.0) * 1.2
            val over = limit != null && v > limit
            BarReading(
                label = "Water need, a year",
                value = "${Fmt.one(v)} acre-ft/acre",
                fill = (v / scale).toFloat(),
                mark = limit?.let { (it / scale).toFloat() },
                markLabel = "limit",
                note = limit?.let { "limit ${Fmt.one(it)}${if (limitIsExample) " (example)" else ""}" } ?: "no limit set",
                warn = over,
                spoken = "Water need ${Fmt.one(v)} acre-feet per acre a year" + (limit?.let { ", limit ${Fmt.one(it)}" } ?: ""),
            )
        }

        // --- greenness: NASA HLS reading, else the calendar's latest clear view ---
        val hls = readings["hls_ndvi"]
        val ndvi = hls?.value ?: latest?.ndvi
        val ndviDate = if (hls?.value != null) hls.obsDate else latest?.date
        val greenness = ndvi?.let {
            BarReading(
                label = "Greenness",
                value = String.format(java.util.Locale.US, "%.2f", it),
                fill = it.coerceIn(0.0, 1.0).toFloat(),
                mark = 0.6f,
                markLabel = "full canopy",
                note = "0 to 1, ${Fmt.dayMonth(ndviDate)}",
                spoken = "Greenness ${String.format(java.util.Locale.US, "%.2f", it)} on a 0 to 1 scale; above 0.6 is a full canopy",
            )
        }

        // --- soil moisture and groundwater percentiles ---
        val soilR = readings["smap_rootzone_pct"] ?: readings["grace_rootzone_pct"]
        val soilFromSmap = readings["smap_rootzone_pct"] != null
        val gwR = readings["grace_gw_pct"]
        val soil = if (soilR?.value != null || gwR?.value != null) {
            val s = soilR?.value?.roundToInt()
            val g = gwR?.value?.roundToInt()
            PercentileReading(
                soil = s, groundwater = g,
                note = "Soil ${s?.let(Fmt::ordinal) ?: "–"}, groundwater ${g?.let(Fmt::ordinal) ?: "–"}",
                spoken = "Soil moisture ${s?.let { Fmt.ordinal(it) + " percentile" } ?: "not available"}, groundwater ${g?.let { Fmt.ordinal(it) + " percentile" } ?: "not available"}; 50 is normal",
            )
        } else null

        // --- the four answers ---
        val answers = buildList {
            val yr = today.year
            val lastRec = hist.keys.maxOrNull()
            val cropLine = when {
                hist[yr] != null -> "${FieldNames.cropName(hist[yr])} on record for $yr."
                lastRec != null -> "$yr crop map not published yet (USDA, early ${yr + 1}). $lastRec: ${FieldNames.cropName(hist[lastRec]).lowercase()}."
                else -> ""
            }
            val sub = when (latestCover) {
                Cover.Partial -> " Some green, less than a full crop: a young crop, regrowth after a cutting, stubble or weeds."
                Cover.Water -> " Standing water on the field."
                else -> ""
            }
            add(
                Answer(
                    question = "What is growing, and how far along?",
                    headline = stateText ?: "No clear satellite view yet",
                    detail = (cropLine + sub).trim(),
                    cite = "NASA/USGS HLS satellites; crop from the USDA Cropland Data Layer." +
                        (latest?.let { " Latest clear view ${Fmt.date(it.date)}." } ?: ""),
                    glossaryIds = listOf("cover_classes", "ndvi"),
                ),
            )
            if (rainMm != null) {
                val inches = Units.mmToInches(rainMm)
                add(
                    Answer(
                        question = "How much rain so far this season?",
                        headline = rainPct?.let { "So far ${vsNormal(it, "wetter than normal", "drier than normal")}" } ?: "${Fmt.one(inches)} inches so far",
                        detail = "${Fmt.one(inches)} in since 1 Oct." + (normalMm?.let { " Normal: ${Fmt.one(Units.mmToInches(it))} in." } ?: ""),
                        cite = "NASA GPM IMERG, to ${Fmt.date(rainObs)}; normal = water years 2001 to 2025.",
                        glossaryIds = listOf("imerg"),
                    ),
                )
            }
            if (needV != null) {
                val lo = need?.low?.let { Fmt.one(it) }
                val hi = need?.high?.let { Fmt.one(it) }
                val rangeText = if (lo != null && hi != null && lo != hi) " (likely $lo to $hi)" else ""
                val over = limit != null && needV > limit
                add(
                    Answer(
                        question = "Will the water limit cover irrigation?",
                        headline = when {
                            limit == null -> "About ${Fmt.one(needV)} acre-feet per acre a year"
                            over -> "Short by about ${Fmt.one(needV - limit)} acre-feet per acre"
                            else -> "Fits your limit in a typical year"
                        },
                        detail = "Needs ${Fmt.one(needV)} acre-ft/acre a year$rangeText." +
                            (limit?.let { " Limit: ${Fmt.one(it)}." } ?: "") +
                            (if (limitIsExample && limit != null) " Example, change it on Compare." else ""),
                        cite = "Rotation model with NASA POWER weather, 2015 to 2025.",
                        glossaryIds = listOf("water_balance", "allocation"),
                        warn = over,
                    ),
                )
            }
            if (soil != null) {
                val s = soilR?.value
                val g = gwR?.value
                val soilWords = s?.let { band(it, "Soil wetter than usual", "Soil about normal", "Soil drier than usual") } ?: "No soil reading"
                val gwWords = g?.let { band(it, "more groundwater than usual", "groundwater about normal", "less groundwater than usual") } ?: "no groundwater reading"
                val details = listOfNotNull(
                    s?.let { "Soil ${Fmt.ordinal(it.roundToInt())} percentile; 50 is normal." },
                    g?.let { "Groundwater ${Fmt.ordinal(it.roundToInt())}, whole basin, not your well." },
                )
                add(
                    Answer(
                        question = "Is the soil wetter or drier than usual? And the groundwater?",
                        headline = "$soilWords; $gwWords",
                        detail = details.joinToString(" "),
                        cite = (if (soilFromSmap) "NASA SMAP and GRACE-FO" else "NASA GRACE-FO") + ", latest ${Fmt.roughly(soilR?.obsDate ?: gwR?.obsDate)}.",
                        glossaryIds = listOf("soil_moisture_pct", "groundwater_grace", "grace"),
                    ),
                )
            }
        }.take(4)

        return FieldNowSummary(strip, rain, waterNeed, greenness, soil, answers)
    }
}
