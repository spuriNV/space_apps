package app.croplytics.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

// ---- GET /api/locations/{id}/calendar: bare / green / flooded calendar from satellite greenness ----

@Serializable
data class CalendarDto(
    @SerialName("data_through") val dataThrough: String? = null,
    val detector: String? = null,
    val source: String? = null,
    @SerialName("disagreement_with_rule_obs_pct") val disagreementPct: Double? = null,
    @SerialName("crop_history") val cropHistory: CalendarCropHistoryDto? = null,
    val years: List<CalendarYearDto> = emptyList(),
    val sources: List<SourceDto> = emptyList(),
)

@Serializable
data class CalendarCropHistoryDto(@SerialName("by_year") val byYear: Map<String, String> = emptyMap())

@Serializable
data class CalendarYearDto(
    val year: Int,
    val segments: List<SegmentDto> = emptyList(),
    val markers: List<MarkerDto> = emptyList(),
    val observations: List<ObservationDto> = emptyList(),
)

@Serializable
data class SegmentDto(
    @SerialName("start_doy") val startDoy: Int = 0,
    @SerialName("end_doy") val endDoy: Int = 0,
    @SerialName("class") val cls: String = "unknown",
)

@Serializable
data class MarkerDto(val date: String = "", val type: String = "", val ndvi: Double? = null)

@Serializable
data class ObservationDto(
    val date: String = "",
    val sensor: String? = null,
    val ndvi: Double? = null,
    @SerialName("class") val cls: String? = null,
)

// ---- GET /api/locations/{id}/nasa_now: latest NASA readings for the field ----

@Serializable
data class ReadingDto(
    val value: Double? = null,
    val step: String? = null,
    @SerialName("obs_date") val obsDate: String? = null,
    @SerialName("stale_steps") val staleSteps: Int? = null,
)

@Serializable
data class NasaNowDto(
    @SerialName("date_requested") val dateRequested: String? = null,
    val readings: Map<String, ReadingDto> = emptyMap(),
    @SerialName("plain_language") val plainLanguage: List<String> = emptyList(),
    @SerialName("latest_by_dataset") val latestByDataset: Map<String, String> = emptyMap(),
    val sources: Map<String, SourceDto> = emptyMap(),
)

// ---- GET /api/locations/{id}/strategies and POST /score: the rotations ----

@Serializable
data class StrategiesDto(val items: List<StrategyDto> = emptyList())

@Serializable
data class ScenarioDto(@SerialName("dT_c") val dTc: Double = 0.0, @SerialName("dP_pct") val dPPct: Double = 0.0)

/** POST /score body: water limit (acre-ft/acre), the grower's priorities (0-4 per score) and a rain / heat what-if. */
@Serializable
data class ScoreRequestDto(val allocation: Double, val weights: Map<String, Double>? = null, val scenario: ScenarioDto? = null)

@Serializable
data class ScoreResponseDto(
    val items: List<StrategyDto> = emptyList(),
    val note: String? = null,
)

@Serializable
data class StrategyCalendarDto(
    val year: Int = 1,
    @SerialName("crop_id") val cropId: String = "",
    val plant: String? = null,
    val harvest: String? = null,
    val role: String? = null,
)

@Serializable
data class ExposureDto(
    val replay: Map<String, ReplayDto> = emptyMap(),
    @SerialName("bare_days_per_year") val bareDays: SourcedNumberDto? = null,
    @SerialName("exposed_rain_days") val exposedRainDays: SourcedNumberDto? = null,
    @SerialName("exposed_heat_days") val exposedHeatDays: SourcedNumberDto? = null,
    @SerialName("exposed_frost_days") val exposedFrostDays: SourcedNumberDto? = null,
)

@Serializable
data class ReplayDto(
    @SerialName("irrigation_need_mm") val irrigationNeedMm: SourcedNumberDto? = null,
    @SerialName("exposed_rain_days") val exposedRainDays: SourcedNumberDto? = null,
)

@Serializable
data class AllocationCheckDto(
    val status: String? = null,
    @SerialName("allocation_af_ac") val allocationAfAc: SourcedNumberDto? = null,
)

@Serializable
data class StrategyWaterDto(
    @SerialName("irrigation_need_af_ac") val irrigationNeedAfAc: SourcedNumberDto? = null,
    @SerialName("irrigation_need_mm") val irrigationNeedMm: SourcedNumberDto? = null,
    @SerialName("etc_vs_openet_pct") val etcVsOpenetPct: SourcedNumberDto? = null,
    @SerialName("etc_by_month_mm") val etcByMonthMm: List<kotlinx.serialization.json.JsonElement> = emptyList(),
    @SerialName("openet_et_mm_season") val openetEtMmSeason: SourcedNumberDto? = null,
    @SerialName("allocation_check") val allocationCheck: AllocationCheckDto? = null,
)

@Serializable
data class CompositeDto(
    val value: Double? = null,
    val low: Double? = null,
    val high: Double? = null,
    val rank: Int? = null,
    @SerialName("tie_note") val tieNote: String? = null,
)

@Serializable
data class ReviewItemDto(val item: String = "", val severity: String? = null)

@Serializable
data class GapDto(val text: String = "")

@Serializable
data class StrategyBriefDto(
    @SerialName("local_review") val localReview: List<ReviewItemDto> = emptyList(),
    val gaps: List<GapDto> = emptyList(),
)

@Serializable
data class StrategyDto(
    val id: String,
    val name: String = "",
    @SerialName("is_baseline") val isBaseline: Boolean = false,
    @SerialName("cycle_years") val cycleYears: Int = 1,
    val calendar: List<StrategyCalendarDto> = emptyList(),
    val exposure: ExposureDto = ExposureDto(),
    val water: StrategyWaterDto = StrategyWaterDto(),
    val scores: Map<String, SourcedNumberDto> = emptyMap(),
    val composite: CompositeDto = CompositeDto(),
    val brief: StrategyBriefDto = StrategyBriefDto(),
)

// ---- GET /api/locations/{id}/outlook: the coming season ----

@Serializable
data class OutlookCategoryDto(
    val category: String? = null,
    @SerialName("valid_season") val validSeason: String? = null,
    val probability: SourcedNumberDto? = null,
)

@Serializable
data class OutlookSeasonDto(
    val lead: Int = 0,
    val season: String = "",
    val temperature: OutlookCategoryDto? = null,
    val precipitation: OutlookCategoryDto? = null,
)

@Serializable
data class CpcOutlookDto(
    val issued: String? = null,
    @SerialName("next_issue") val nextIssue: String? = null,
    val seasons: List<OutlookSeasonDto> = emptyList(),
)

@Serializable
data class DroughtMonitorDto(
    @SerialName("worst_category") val worstCategory: String? = null,
    @SerialName("worst_category_code") val worstCategoryCode: String? = null,
    @SerialName("map_date") val mapDate: String? = null,
    val county: String? = null,
)

@Serializable
data class DroughtOutlookItemDto(val category: String? = null, val target: String? = null)

@Serializable
data class DroughtOutlookDto(val seasonal: DroughtOutlookItemDto? = null)

@Serializable
data class DroughtDto(
    @SerialName("us_drought_monitor") val usDroughtMonitor: DroughtMonitorDto? = null,
    @SerialName("cpc_drought_outlook") val cpcDroughtOutlook: DroughtOutlookDto? = null,
)

@Serializable
data class ReservoirDto(
    val name: String? = null,
    @SerialName("cdec_report_date") val reportDate: String? = null,
    @SerialName("storage_af") val storageAf: SourcedNumberDto? = null,
    @SerialName("pct_of_capacity") val pctOfCapacity: SourcedNumberDto? = null,
    @SerialName("pct_of_cdec_average") val pctOfAverage: SourcedNumberDto? = null,
    @SerialName("pct_of_own_average") val pctOfOwnAverage: SourcedNumberDto? = null,
    @SerialName("storage_year_ago_af") val storageYearAgoAf: SourcedNumberDto? = null,
    @SerialName("latest_daily_date") val latestDailyDate: String? = null,
)

@Serializable
data class NotYetDto(val status: String? = null, val note: String? = null)

@Serializable
data class CvpDto(
    val wy2026: Map<String, SourcedNumberDto> = emptyMap(),
    @SerialName("wy2027_initial") val wy2027Initial: NotYetDto? = null,
)

@Serializable
data class SwpDto(
    val latest: SourcedNumberDto? = null,
    @SerialName("wy2027_initial") val wy2027Initial: NotYetDto? = null,
)

@Serializable
data class StorageAllocRowDto(
    @SerialName("allocation_year") val allocationYear: Int = 0,
    @SerialName("pct_of_capacity") val pctOfCapacity: Double? = null,
    @SerialName("cvp_south_of_delta_ag_pct") val southAg: Double? = null,
    @SerialName("cvp_settlement_contractors_pct") val settlement: Double? = null,
    @SerialName("partial_year") val partial: Boolean? = null,
)

@Serializable
data class StorageVsAllocDto(
    val rows: List<StorageAllocRowDto> = emptyList(),
    @SerialName("shasta_13nov_2026_af") val shastaNowAf: Double? = null,
)

@Serializable
data class AllocationsContextDto(
    val cvp: CvpDto? = null,
    val swp: SwpDto? = null,
    @SerialName("storage_vs_final_allocation") val storageVsAlloc: StorageVsAllocDto? = null,
)

@Serializable
data class SnowNowDto(@SerialName("swe_inches") val sweInches: SourcedNumberDto? = null, @SerialName("report_date") val reportDate: String? = null)

@Serializable
data class Bulletin120Dto(val status: String? = null)

@Serializable
data class SnowpackDto(@SerialName("snow_now_statewide") val snowNow: SnowNowDto? = null, @SerialName("bulletin_120") val bulletin120: Bulletin120Dto? = null)

@Serializable
data class BareWindowDto(
    @SerialName("median_start") val medianStart: String? = null,
    @SerialName("median_end") val medianEnd: String? = null,
    @SerialName("median_days") val medianDays: SourcedNumberDto? = null,
)

@Serializable
data class HeavyRainDto(
    @SerialName("chance_any_day_ge_25mm_climatology") val chanceClimatology: SourcedNumberDto? = null,
    @SerialName("chance_given_cpc_outlook") val chanceGivenOutlook: SourcedNumberDto? = null,
    @SerialName("cpc_precip_category") val cpcPrecipCategory: String? = null,
)

@Serializable
data class FieldExpectationsDto(
    @SerialName("current_crop") val currentCrop: String? = null,
    @SerialName("bare_window") val bareWindow: BareWindowDto? = null,
    @SerialName("heavy_rain_in_window") val heavyRainInWindow: HeavyRainDto? = null,
)

@Serializable
data class RangeDto(val low: Double? = null, val high: Double? = null)

@Serializable
data class IrrigationStrategyDto(
    val id: String = "",
    val name: String = "",
    @SerialName("is_baseline") val isBaseline: Boolean = false,
    @SerialName("irrigation_need_af_ac") val irrigationNeedAfAc: SourcedNumberDto? = null,
    @SerialName("engine_param_range") val engineParamRange: RangeDto? = null,
)

@Serializable
data class Irrigation2027Dto(val strategies: List<IrrigationStrategyDto> = emptyList())

@Serializable
data class BlockedItemDto(val item: String = "", val status: String? = null)

@Serializable
data class OutlookDto(
    val today: String? = null,
    @SerialName("coming_season") val comingSeason: String? = null,
    val county: String? = null,
    @SerialName("cpc_seasonal_outlook") val cpc: CpcOutlookDto? = null,
    val drought: DroughtDto? = null,
    @SerialName("reservoirs_now") val reservoirsNow: Map<String, ReservoirDto> = emptyMap(),
    @SerialName("allocations_context") val allocations: AllocationsContextDto? = null,
    @SerialName("field_expectations_from_history") val fieldExpectations: FieldExpectationsDto? = null,
    @SerialName("irrigation_2027") val irrigation2027: Irrigation2027Dto? = null,
    @SerialName("plain_language_summary") val plainLanguageSummary: String? = null,
    @SerialName("snowpack_runoff") val snowpack: SnowpackDto? = null,
    @SerialName("blocked_or_not_yet_published") val blocked: List<BlockedItemDto> = emptyList(),
)

// ---- "More detail" routes ----

@Serializable
data class ModelSplitDto(@SerialName("test_years") val testYears: List<Int> = emptyList())

@Serializable
data class ModelDto(
    val id: String = "",
    val task: String = "",
    val method: String = "",
    val split: ModelSplitDto? = null,
    val metrics: JsonObject? = null,
)

@Serializable
data class ModelsDto(val items: List<ModelDto> = emptyList())

@Serializable
data class OpenEtAnnualDto(val year: Int = 0, @SerialName("et_mm") val etMm: Double? = null, val months: Int = 0)

@Serializable
data class OpenEtDto(val annual: List<OpenEtAnnualDto> = emptyList(), val rows: List<OpenEtRowDto> = emptyList(), val note: String? = null)

@Serializable
data class OpenEtRowDto(val date: String = "", val month: String? = null, @SerialName("et_in") val etIn: Double? = null, @SerialName("et_mm") val etMm: Double? = null)

@Serializable
data class GlossaryItemDto(
    val id: String = "",
    val term: String = "",
    val short: String = "",
    @SerialName("source_url") val sourceUrl: String? = null,
)

@Serializable
data class GlossaryDto(val items: List<GlossaryItemDto> = emptyList())

@Serializable
data class WaterSeasonDto(
    val season: String = "",
    @SerialName("clear_scenes") val clearScenes: Int = 0,
    @SerialName("max_water_frac") val maxWaterFrac: Double? = null,
    @SerialName("water_seen") val waterSeen: Boolean? = null,
)

@Serializable
data class WaterSeenDto(val summary: String? = null, val seasons: List<WaterSeasonDto> = emptyList(), val scenes: List<WaterSceneDto> = emptyList())

@Serializable
data class WaterSceneDto(val date: String = "", @SerialName("water_frac") val waterFrac: Double? = null, val clear: Boolean = false)

@Serializable
data class StressYearDto(
    val crop: String? = null,
    val weeks: Int = 0,
    val evaluated: Int = 0,
    @SerialName("flag_zscore") val flagZscore: Int = 0,
    @SerialName("flag_iforest") val flagIforest: Int = 0,
)

@Serializable
data class StressSummaryDto(@SerialName("by_year") val byYear: Map<String, StressYearDto> = emptyMap())

@Serializable
data class StressDto(val summary: StressSummaryDto? = null, val weeks: List<StressWeekDto> = emptyList())

@Serializable
data class StressWeekDto(
    @SerialName("week_start") val weekStart: String = "",
    @SerialName("iso_year") val isoYear: Int? = null,
    val status: String? = null,
    val drivers: List<String> = emptyList(),
    @SerialName("tmax_c") val tmaxC: Double? = null,
    val crop: String? = null,
    val evaluated: Boolean? = null,
)

@Serializable
data class InsuranceProfileDto(
    val scope: String? = null,
    val crop: String? = null,
    @SerialName("total_indemnity_usd") val totalIndemnityUsd: Double? = null,
    @SerialName("indemnity_by_year_usd") val byYear: Map<String, Double> = emptyMap(),
    val shares: Map<String, SourcedNumberDto> = emptyMap(),
)

@Serializable
data class InsuranceDto(val years: List<Int> = emptyList(), val profiles: Map<String, InsuranceProfileDto> = emptyMap(), @SerialName("page_url") val pageUrl: String? = null)
