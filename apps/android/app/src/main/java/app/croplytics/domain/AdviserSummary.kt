package app.croplytics.domain

import app.croplytics.data.remote.dto.StrategyDto
import java.time.LocalDate

/** The one-page summary for the grower's adviser (PLAN.md "Brief"), fixed templates, no LLM. */
data class AdviserSummary(
    val fieldName: String,
    val fieldLine: String,
    val stateFieldNo: String?,
    val preparedOn: String,
    val now: List<Answer>,
    val season: List<Answer>,
    val limitLine: String?,
    val today: String,
    val option: OptionComparison?,
    val checkLocally: List<String>,
    val sources: List<String>,
) {
    val fileName: String
        get() = "CropLytics summary - ${fieldName.replace(Regex("[^A-Za-z0-9 .-]"), "").take(60)}.pdf"
}

object AdviserSummaryBuilder {
    /** NASA first, then the others (skill: "NASA first"). */
    val SOURCES = listOf(
        "NASA GPM IMERG satellite rain",
        "NASA GRACE-FO groundwater and root-zone soil moisture (and SMAP when available)",
        "NASA/USGS HLS, Landsat and ESA Sentinel-2 imagery for the bare / green / flooded calendar",
        "NASA POWER daily weather, used by the rotation model",
        "USDA Cropland Data Layer (crops by year); USDA soil survey (SSURGO)",
        "NOAA Climate Prediction Center outlooks; US Drought Monitor",
        "California Data Exchange Center (reservoirs); Reclamation and DWR allocations",
        "OpenET measured water use, as a check on the model",
    )

    fun build(
        identity: FieldIdentity,
        now: FieldNowSummary?,
        season: ComingSeasonSummary?,
        compare: CompareSummary?,
        chosen: OptionComparison?,
        strategies: List<StrategyDto>?,
        limit: Double?,
        limitIsExample: Boolean,
        today: LocalDate,
    ): AdviserSummary {
        val chosenStrategy = strategies?.firstOrNull { it.id == chosen?.id }
        val check = chosenStrategy?.brief?.localReview.orEmpty()
            .filter { it.severity == "high" || it.severity == "medium" }
            .map { it.item.replace(Regex("\\s*\\((spec [^)]*|U)\\)"), "").trim().trimEnd('.') + "." }
            .ifEmpty { listOf("Every alternative rotation needs review by the grower and an adviser before anything is seeded.") }
        return AdviserSummary(
            fieldName = identity.name,
            fieldLine = identity.subtitle,
            stateFieldNo = identity.stateFieldNo,
            preparedOn = Fmt.date(today),
            now = now?.answers.orEmpty(),
            season = season?.items.orEmpty(),
            limitLine = limit?.let { "Water limit used: ${Fmt.one(it)} acre-ft/acre a year${if (limitIsExample) " (an example; the grower's own limit should replace it)" else " (set by the grower)"}." },
            today = compare?.today?.let { t ->
                "${t.name}: " + (t.need?.let { "about ${Fmt.one(it.value)} acre-ft/acre a year (likely ${Fmt.one(it.low)} to ${Fmt.one(it.high)})" } ?: "water need not worked out")
            } ?: "Not worked out yet",
            option = chosen,
            checkLocally = check.take(4),
            sources = SOURCES,
        )
    }
}
