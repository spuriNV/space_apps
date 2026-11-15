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
import kotlinx.coroutines.flow.flowOf
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
    /** BC: the First Nations card; reserve outlines near the field (context only). */
    fun firstNations(id: String): Flow<LoadState<app.croplytics.data.remote.dto.FirstNationsDto>>
    /** Nation tools: one small JSON route under /locations/{id}/ (404 becomes NotAvailable). `path` is relative, such as "nation/funding?jurisdiction=BC". */
    fun route(id: String, path: String): Flow<LoadState<kotlinx.serialization.json.JsonObject>>
    /** BC: the salmon route, cut down to what the phone shows (the full reply carries 4,000 daily rows). */
    fun salmon(id: String): Flow<LoadState<kotlinx.serialization.json.JsonObject>>
    fun reserves(id: String): Flow<LoadState<List<app.croplytics.domain.Reserve>>>

    /** Re-scores the rotations (POST /score) for a water limit, the grower's priorities and a rain / heat what-if. Cached per request. */
    fun score(id: String, limitAfAc: Double, weights: Map<String, Double>? = null, scenario: ScenarioDto? = null): Flow<LoadState<List<StrategyDto>>>

    fun waterLimit(id: String): Flow<Double?>
    suspend fun setWaterLimit(id: String, acreFeetPerAcre: Double)

    // ---------- 1.3.0: this week, tapped spots, the farm catalog, Ask, drawn fields (defaults keep older fakes working) ----------

    /** GET /locations/{id}/this_week as raw JSON (parsed by WeekLogic); NotAvailable for ids the route does not serve. */
    fun week(id: String): Flow<LoadState<kotlinx.serialization.json.JsonObject>> = flowOf(LoadState.Failed(LoadError.NotAvailable))
    /** GET /catalog as raw JSON (parsed by CatalogLogic). */
    fun catalog(): Flow<LoadState<kotlinx.serialization.json.JsonObject>> = flowOf(LoadState.Failed(LoadError.NotAvailable))
    /** GET /analyze?lat=&lon= for a tapped spot (a `pt_` id). */
    suspend fun analyze(lat: Double, lon: Double): SpotResult = SpotResult.Error("Spots are not available right now.")
    /** The catalog's own `pt_` spot (GET /locations/{id}; falls back to analysing its coordinates). */
    suspend fun spot(id: String, lat: Double, lon: Double): SpotResult = analyze(lat, lon)
    /** POST /my-fields with one polygon ring (lon, lat). */
    suspend fun createField(name: String, ring: List<Pair<Double, Double>>): SpotResult = SpotResult.Error("Drawing is not available right now.")
    /** Whether the API has the Ask CropLytics chat switched on. */
    suspend fun chatEnabled(): Boolean = false
    /** POST /chat; the answer, or an error whose message is safe to show. */
    suspend fun ask(question: String, history: List<Pair<String, String>>, fieldId: String?, screen: String, date: String, waterLimit: Double?): AskResult = AskResult.Error("Ask is not available right now.")
}

/** A tapped spot, a catalog spot or a drawn field as the API answers. */
sealed interface SpotResult {
    data class Ok(val loc: app.croplytics.data.remote.dto.LocationDto) : SpotResult
    /** The tap landed on a prepared field. */
    data class Preset(val id: String) : SpotResult
    data class Error(val message: String) : SpotResult
}

sealed interface AskResult {
    data class Answer(val text: String) : AskResult
    data class Error(val message: String) : AskResult
}
