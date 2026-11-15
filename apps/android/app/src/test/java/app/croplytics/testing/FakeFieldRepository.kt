package app.croplytics.testing

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
import app.croplytics.data.repository.CalendarBundle
import app.croplytics.data.repository.FieldRepository
import app.croplytics.data.repository.IssPhoto
import app.croplytics.data.repository.LoadError
import app.croplytics.data.repository.LoadState
import app.croplytics.domain.CellGrid
import app.croplytics.domain.Daily
import app.croplytics.domain.RegionalSeries
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import java.time.Instant

/** In-memory repository: each part is a StateFlow the test sets directly. */
class FakeFieldRepository : FieldRepository {
    val savedAt: Instant = Instant.parse("2026-11-14T20:00:00Z")
    fun <T> ready(v: T) = LoadState.Ready(v, savedAt)
    private fun <T> missing(): Flow<LoadState<T>> = flowOf(LoadState.Failed(LoadError.NotAvailable))

    val locations = MutableStateFlow<LoadState<List<LocationDto>>>(LoadState.Loading)
    val calendar = MutableStateFlow<LoadState<CalendarBundle>>(LoadState.Loading)
    val regional = MutableStateFlow<LoadState<RegionalSeries>>(LoadState.Loading)
    val nasaNow = MutableStateFlow<LoadState<NasaNowDto>>(LoadState.Loading)
    val strategies = MutableStateFlow<LoadState<List<StrategyDto>>>(LoadState.Loading)
    val outlook = MutableStateFlow<LoadState<OutlookDto>>(LoadState.Loading)
    val limits = MutableStateFlow<Map<String, Double>>(emptyMap())

    /** Every POST /score the view model asked for: limit, weights, scenario. */
    val scoreRequests = mutableListOf<Triple<Double, Map<String, Double>?, ScenarioDto?>>()
    var scoreResult: (Double) -> LoadState<List<StrategyDto>> = { LoadState.Failed(LoadError.Server) }
    var forcedReloads = 0

    override fun locations(force: Boolean): Flow<LoadState<List<LocationDto>>> { if (force) forcedReloads++; return locations }
    override fun location(id: String, force: Boolean): Flow<LoadState<LocationDto>> = locations.map { s -> (s as? LoadState.Ready)?.let { r -> r.data.firstOrNull { it.id == id }?.let(::ready) } ?: LoadState.Loading }
    override fun calendar(id: String, force: Boolean) = calendar
    override fun strip(id: String): Flow<LoadState<Map<Int, String>>> = flowOf(ready(mapOf(2026 to "c".repeat(36))))
    override fun regional(id: String, force: Boolean) = regional
    override fun nasaNow(id: String, force: Boolean) = nasaNow
    override fun daily(id: String, force: Boolean): Flow<LoadState<Daily>> = missing()
    override fun grid(id: String, force: Boolean): Flow<LoadState<CellGrid>> = missing()
    override fun strategies(id: String, force: Boolean) = strategies
    override fun outlook(id: String, force: Boolean) = outlook
    override fun openet(id: String, force: Boolean): Flow<LoadState<OpenEtDto>> = missing()
    override fun waterSeen(id: String, force: Boolean): Flow<LoadState<WaterSeenDto>> = missing()
    override fun stress(id: String, force: Boolean): Flow<LoadState<StressDto>> = missing()
    override fun insurance(id: String, force: Boolean): Flow<LoadState<InsuranceDto>> = missing()
    override fun iss(id: String): Flow<LoadState<IssPhoto?>> = flowOf(ready(null))
    override fun glossary(force: Boolean): Flow<LoadState<GlossaryDto>> = flowOf(ready(GlossaryDto()))
    override fun firstNations(id: String): Flow<LoadState<app.croplytics.data.remote.dto.FirstNationsDto>> = missing()
    override fun route(id: String, path: String): Flow<LoadState<kotlinx.serialization.json.JsonObject>> = missing()
    override fun salmon(id: String): Flow<LoadState<kotlinx.serialization.json.JsonObject>> = missing()
    override fun reserves(id: String): Flow<LoadState<List<app.croplytics.domain.Reserve>>> = missing()

    override fun score(id: String, limitAfAc: Double, weights: Map<String, Double>?, scenario: ScenarioDto?): Flow<LoadState<List<StrategyDto>>> {
        scoreRequests += Triple(limitAfAc, weights, scenario)
        return flowOf(scoreResult(limitAfAc))
    }

    override fun waterLimit(id: String): Flow<Double?> = limits.map { it[id] }
    override suspend fun setWaterLimit(id: String, acreFeetPerAcre: Double) { limits.value = limits.value + (id to acreFeetPerAcre) }
}
