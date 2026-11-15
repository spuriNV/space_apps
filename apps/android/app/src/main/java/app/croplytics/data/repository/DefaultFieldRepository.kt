package app.croplytics.data.repository

import app.croplytics.data.local.CacheDao
import app.croplytics.data.local.CachedResponseEntity
import app.croplytics.data.local.FieldPrefs
import app.croplytics.data.remote.CropLyticsApi
import app.croplytics.data.remote.dto.CalendarDto
import app.croplytics.data.remote.dto.GlossaryDto
import app.croplytics.data.remote.dto.InsuranceDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.LocationsDto
import app.croplytics.data.remote.dto.ModelsDto
import app.croplytics.data.remote.dto.NasaNowDto
import app.croplytics.data.remote.dto.OpenEtDto
import app.croplytics.data.remote.dto.OutlookDto
import app.croplytics.data.remote.dto.ScoreRequestDto
import app.croplytics.data.remote.dto.StrategiesDto
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.remote.dto.StressDto
import app.croplytics.data.remote.dto.WaterSeenDto
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.channelFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.KSerializer
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json
import retrofit2.HttpException
import java.io.IOException
import java.net.SocketTimeoutException
import java.time.Clock
import java.time.Instant
import java.util.Locale

/** Timing rules for the repository; tests shorten them. */
data class RepositoryConfig(
    /** After this long without an answer (and nothing saved), say the server is waking up. */
    val wakeAfterMs: Long = 3_500,
    /** A saved copy younger than this is shown without asking the server again. */
    val freshForMs: Long = 10 * 60 * 1000,
)

class DefaultFieldRepository(
    private val api: CropLyticsApi,
    private val dao: CacheDao,
    private val prefs: FieldPrefs,
    private val json: Json,
    /** Application-lifetime scope: a fetch started by one screen finishes even if that screen goes away. */
    private val appScope: CoroutineScope,
    private val clock: Clock = Clock.systemUTC(),
    private val config: RepositoryConfig = RepositoryConfig(),
) : FieldRepository {

    private val inFlightLock = Mutex()
    private val inFlight = HashMap<String, Deferred<CachedResponseEntity>>()

    override fun locations(force: Boolean) =
        cached("locations", LocationsDto.serializer(), force) { api.locations() }.map { s -> s.map { it.items } }

    override fun location(id: String, force: Boolean) = cached("location/$id", LocationDto.serializer(), force) { api.location(id) }
    override fun calendar(id: String, force: Boolean) = cached("calendar/$id", CalendarDto.serializer(), force) { api.calendar(id) }
    override fun nasaNow(id: String, force: Boolean) = cached("nasa_now/$id", NasaNowDto.serializer(), force) { api.nasaNow(id) }
    override fun strategies(id: String, force: Boolean) =
        cached("strategies/$id", StrategiesDto.serializer(), force) { api.strategies(id) }.map { s -> s.map { it.items } }

    override fun outlook(id: String, force: Boolean) = cached("outlook/$id", OutlookDto.serializer(), force) { api.outlook(id) }
    override fun models(id: String, force: Boolean) = cached("models/$id", ModelsDto.serializer(), force) { api.models(id) }
    override fun openet(id: String, force: Boolean) = cached("openet/$id", OpenEtDto.serializer(), force) { api.openet(id) }
    override fun waterSeen(id: String, force: Boolean) = cached("water_seen/$id", WaterSeenDto.serializer(), force) { api.waterSeen(id) }
    override fun stress(id: String, force: Boolean) = cached("stress/$id", StressDto.serializer(), force) { api.stress(id) }
    override fun insurance(id: String, force: Boolean) = cached("insurance/$id", InsuranceDto.serializer(), force) { api.insurance(id) }
    override fun glossary(force: Boolean) = cached("glossary", GlossaryDto.serializer(), force) { api.glossary() }

    override fun score(id: String, limitAfAc: Double): Flow<LoadState<List<StrategyDto>>> {
        val key = "score/$id/${String.format(Locale.US, "%.2f", limitAfAc)}"
        return cached(key, ListSerializer(StrategyDto.serializer()), force = false) {
            api.score(id, ScoreRequestDto(allocation = limitAfAc)).items
        }
    }

    override fun waterLimit(id: String): Flow<Double?> = prefs.waterLimit(id)
    override suspend fun setWaterLimit(id: String, acreFeetPerAcre: Double) = prefs.setWaterLimit(id, acreFeetPerAcre)

    /**
     * Offline-first read of one API response:
     * 1. a saved copy that is fresh enough is shown and the server is not asked;
     * 2. otherwise the saved copy (if any) shows while the server is asked;
     * 3. no saved copy and a slow server means it is waking up ([LoadState.Waking]);
     * 4. on failure the saved copy stays, marked offline, or the error is shown.
     */
    private fun <T> cached(
        key: String,
        serializer: KSerializer<T>,
        force: Boolean,
        fetch: suspend () -> T,
    ): Flow<LoadState<T>> = channelFlow {
        val saved = dao.get(key)?.let { row ->
            runCatching { json.decodeFromString(serializer, row.json) }.getOrNull()
                ?.let { it to Instant.ofEpochMilli(row.savedAtEpochMs) }
        }
        if (saved != null && !force && clock.millis() - saved.second.toEpochMilli() < config.freshForMs) {
            send(LoadState.Ready(saved.first, saved.second))
            return@channelFlow
        }
        send(if (saved != null) LoadState.Ready(saved.first, saved.second, refreshing = true) else LoadState.Loading)
        val waking = launch {
            delay(config.wakeAfterMs)
            if (saved == null) send(LoadState.Waking)
        }
        try {
            val row = shared(key) {
                val value = fetch()
                CachedResponseEntity(key, json.encodeToString(serializer, value), clock.millis()).also { dao.put(it) }
            }
            waking.cancel()
            send(LoadState.Ready(json.decodeFromString(serializer, row.json), Instant.ofEpochMilli(row.savedAtEpochMs)))
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            waking.cancel()
            send(if (saved != null) LoadState.Ready(saved.first, saved.second, offline = true) else LoadState.Failed(classify(e)))
        }
    }

    /** One network request per key at a time: four tabs asking for the same field share one call. */
    private suspend fun shared(key: String, block: suspend () -> CachedResponseEntity): CachedResponseEntity {
        val deferred = inFlightLock.withLock {
            inFlight[key]?.takeIf { it.isActive } ?: appScope.async {
                try {
                    block()
                } finally {
                    inFlightLock.withLock { inFlight.remove(key) }
                }
            }.also { inFlight[key] = it }
        }
        return deferred.await()
    }

    private fun classify(e: Throwable): LoadError = when (e) {
        is HttpException -> if (e.code() == 404) LoadError.NotAvailable else LoadError.Server
        is SocketTimeoutException -> LoadError.Server
        is IOException -> LoadError.NoConnection
        else -> LoadError.Server
    }
}
