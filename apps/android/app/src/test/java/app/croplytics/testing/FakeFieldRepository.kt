package app.croplytics.testing

import app.croplytics.data.remote.dto.CalendarDto
import app.croplytics.data.remote.dto.GlossaryDto
import app.croplytics.data.remote.dto.InsuranceDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.ModelsDto
import app.croplytics.data.remote.dto.NasaNowDto
import app.croplytics.data.remote.dto.OpenEtDto
import app.croplytics.data.remote.dto.OutlookDto
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.remote.dto.StressDto
import app.croplytics.data.remote.dto.WaterSeenDto
import app.croplytics.data.repository.FieldRepository
import app.croplytics.data.repository.LoadError
import app.croplytics.data.repository.LoadState
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.map
import java.time.Instant

/** In-memory repository: each part is a StateFlow the test sets directly. */
class FakeFieldRepository : FieldRepository {
    val savedAt: Instant = Instant.parse("2026-11-14T20:00:00Z")
    fun <T> ready(v: T) = LoadState.Ready(v, savedAt)

    val locations = MutableStateFlow<LoadState<List<LocationDto>>>(LoadState.Loading)
    val location = MutableStateFlow<LoadState<LocationDto>>(LoadState.Loading)
    val calendar = MutableStateFlow<LoadState<CalendarDto>>(LoadState.Loading)
    val nasaNow = MutableStateFlow<LoadState<NasaNowDto>>(LoadState.Loading)
    val strategies = MutableStateFlow<LoadState<List<StrategyDto>>>(LoadState.Loading)
    val outlook = MutableStateFlow<LoadState<OutlookDto>>(LoadState.Loading)
    val limits = MutableStateFlow<Map<String, Double>>(emptyMap())

    /** Limits the ViewModel asked to score, in order. */
    val scoreRequests = mutableListOf<Double>()
    var scoreResult: (Double) -> LoadState<List<StrategyDto>> = { LoadState.Failed(LoadError.Server) }
    var forcedReloads = 0

    private fun <T> track(force: Boolean, f: Flow<T>): Flow<T> { if (force) forcedReloads++; return f }

    override fun locations(force: Boolean) = track(force, locations)
    override fun location(id: String, force: Boolean) = track(force, location)
    override fun calendar(id: String, force: Boolean) = track(force, calendar)
    override fun nasaNow(id: String, force: Boolean) = track(force, nasaNow)
    override fun strategies(id: String, force: Boolean) = track(force, strategies)
    override fun outlook(id: String, force: Boolean) = track(force, outlook)
    override fun models(id: String, force: Boolean): Flow<LoadState<ModelsDto>> = MutableStateFlow(LoadState.Failed(LoadError.NotAvailable))
    override fun openet(id: String, force: Boolean): Flow<LoadState<OpenEtDto>> = MutableStateFlow(LoadState.Failed(LoadError.NotAvailable))
    override fun waterSeen(id: String, force: Boolean): Flow<LoadState<WaterSeenDto>> = MutableStateFlow(LoadState.Failed(LoadError.NotAvailable))
    override fun stress(id: String, force: Boolean): Flow<LoadState<StressDto>> = MutableStateFlow(LoadState.Failed(LoadError.NotAvailable))
    override fun insurance(id: String, force: Boolean): Flow<LoadState<InsuranceDto>> = MutableStateFlow(LoadState.Failed(LoadError.NotAvailable))
    override fun glossary(force: Boolean): Flow<LoadState<GlossaryDto>> = MutableStateFlow(LoadState.Ready(GlossaryDto(), savedAt))

    override fun score(id: String, limitAfAc: Double): Flow<LoadState<List<StrategyDto>>> {
        scoreRequests += limitAfAc
        return MutableStateFlow(scoreResult(limitAfAc))
    }

    override fun waterLimit(id: String): Flow<Double?> = limits.map { it[id] }
    override suspend fun setWaterLimit(id: String, acreFeetPerAcre: Double) { limits.value = limits.value + (id to acreFeetPerAcre) }
}
