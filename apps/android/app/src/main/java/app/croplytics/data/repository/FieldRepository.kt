package app.croplytics.data.repository

import app.croplytics.data.remote.dto.GlossaryDto
import app.croplytics.data.remote.dto.InsuranceDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.NasaNowDto
import app.croplytics.data.remote.dto.OpenEtDto
import app.croplytics.data.remote.dto.OutlookDto
import app.croplytics.data.remote.dto.ScenarioDto
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.remote.dto.StressDto
import app.croplytics.data.remote.dto.WaterSeenDto
import app.croplytics.domain.CellGrid
import app.croplytics.domain.Daily
import app.croplytics.domain.FieldCalendar
import app.croplytics.domain.MLInfo
import app.croplytics.domain.RegionalSeries
import kotlinx.coroutines.flow.Flow
import kotlinx.serialization.Serializable

/** The field calendar (HLS when served, else Landsat / Sentinel-2) with the machine-learning comparison. */
@Serializable
data class CalendarBundle(val calendar: FieldCalendar, val ml: MLInfo?)

/** The astronaut photo nearest the field (served by the web app under /iss/<id>/). */
@Serializable
data class IssPhoto(val photoId: String, val date: String, val features: String, val pageUrl: String, val url: String, val miles: Double, val credit: String)

/**
 * Single source of truth for field data, one call per web-app route. Every call is offline-first: the copy saved on the
 * phone comes first (if any), then the server's answer replaces it. `force = true` skips the "fresh enough" shortcut.
 */
interface FieldRepository {
    fun locations(force: Boolean = false): Flow<LoadState<List<LocationDto>>>
    fun location(id: String, force: Boolean = false): Flow<LoadState<LocationDto>>
    fun calendar(id: String, force: Boolean = false): Flow<LoadState<CalendarBundle>>
    /** 2023 to this year as 36 classes per year, for the pick list. */
    fun strip(id: String): Flow<LoadState<Map<Int, String>>>
    fun regional(id: String, force: Boolean = false): Flow<LoadState<RegionalSeries>>
    fun nasaNow(id: String, force: Boolean = false): Flow<LoadState<NasaNowDto>>
    fun daily(id: String, force: Boolean = false): Flow<LoadState<Daily>>
    fun grid(id: String, force: Boolean = false): Flow<LoadState<CellGrid>>
    fun strategies(id: String, force: Boolean = false): Flow<LoadState<List<StrategyDto>>>
    fun outlook(id: String, force: Boolean = false): Flow<LoadState<OutlookDto>>
    fun openet(id: String, force: Boolean = false): Flow<LoadState<OpenEtDto>>
    fun waterSeen(id: String, force: Boolean = false): Flow<LoadState<WaterSeenDto>>
    fun stress(id: String, force: Boolean = false): Flow<LoadState<StressDto>>
    fun insurance(id: String, force: Boolean = false): Flow<LoadState<InsuranceDto>>
    fun iss(id: String): Flow<LoadState<IssPhoto?>>
    fun glossary(force: Boolean = false): Flow<LoadState<GlossaryDto>>

    /** Re-scores the rotations (POST /score) for a water limit, the grower's priorities and a rain / heat what-if. Cached per request. */
    fun score(id: String, limitAfAc: Double, weights: Map<String, Double>? = null, scenario: ScenarioDto? = null): Flow<LoadState<List<StrategyDto>>>

    fun waterLimit(id: String): Flow<Double?>
    suspend fun setWaterLimit(id: String, acreFeetPerAcre: Double)
}
