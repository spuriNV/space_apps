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
import app.croplytics.data.remote.dto.NasaNowDto
import app.croplytics.data.remote.dto.OpenEtDto
import app.croplytics.data.remote.dto.OutlookDto
import app.croplytics.data.remote.dto.ScenarioDto
import app.croplytics.data.remote.dto.ScoreRequestDto
import app.croplytics.data.remote.dto.StrategiesDto
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.remote.dto.StressDto
import app.croplytics.data.remote.dto.WaterSeenDto
import app.croplytics.domain.Calendars
import app.croplytics.domain.CellGrid
import app.croplytics.domain.Daily
import app.croplytics.domain.Parsers
import app.croplytics.domain.RegionalSeries
import app.croplytics.domain.Timeline
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
import kotlinx.serialization.builtins.MapSerializer
import kotlinx.serialization.builtins.nullable
import kotlinx.serialization.builtins.serializer
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import retrofit2.HttpException
import java.io.IOException
import java.net.SocketTimeoutException
import java.time.Clock
import java.time.Instant
import java.time.LocalDate
import java.util.Locale
import kotlin.math.cos
import kotlin.math.hypot

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
    /** Big payloads (daily record, 30 m grid); defaults to the Room cache. */
    private val blobs: CacheDao = dao,
    /** Where the web app's own files are served (ISS photos), e.g. https://croplytics-app.onrender.com/ */
    private val webBase: String = "https://croplytics-app.onrender.com/",
) : FieldRepository {

    private val inFlightLock = Mutex()
    private val inFlight = HashMap<String, Deferred<CachedResponseEntity>>()
    private val years get() = Timeline.years(LocalDate.now(clock))

    override fun locations(force: Boolean) =
        cached("locations", LocationsDto.serializer(), force) { api.locations() }.map { s -> s.map { it.items } }

    override fun location(id: String, force: Boolean) = cached("location/$id", LocationDto.serializer(), force) { api.location(id) }

    override fun calendar(id: String, force: Boolean) = cached("calendar2/$id", CalendarBundle.serializer(), force) {
        // NASA first: the HLS calendar wins when the API serves it (api.ts getField)
        val hls = optional { api.calendar(id, "hls") }?.takeIf { it.years.isNotEmpty() && (it.source?.contains("hls", true) == true) }
        val rule = hls ?: api.calendar(id)
        val ml = optional { api.calendarMl(id) }?.takeIf { it.years.isNotEmpty() }
        val models = if (ml != null) optional { api.models(id) } else null
        val hist = rule.cropHistory?.byYear.orEmpty().mapNotNull { (y, c) -> y.toIntOrNull()?.let { it to c } }.toMap()
        CalendarBundle(Calendars.convert(id, rule, ml, hist, years, hls != null), ml?.let { Parsers.ml(models, it.detector, it.disagreementPct) })
    }

    override fun strip(id: String) = cached("strip/$id", MapSerializer(Int.serializer(), String.serializer()), false) {
        val c: CalendarDto = optional { api.calendar(id, "hls") }?.takeIf { it.years.isNotEmpty() } ?: api.calendar(id)
        (Timeline.RECENT_FROM..LocalDate.now(clock).year).associateWith { y -> Calendars.classString(c.years.firstOrNull { it.year == y }, y) }
    }

    override fun regional(id: String, force: Boolean) = cached("regional/$id", RegionalSeries.serializer(), force) { Parsers.regional(api.nasaSeries(id), years) }
    override fun nasaNow(id: String, force: Boolean) = cached("nasa_now/$id", NasaNowDto.serializer(), force) { api.nasaNow(id) }
    override fun daily(id: String, force: Boolean) = cached("daily/$id", Daily.serializer(), force, blobs) { Parsers.daily(api.daily(id)) }
    override fun grid(id: String, force: Boolean) = cached("grid/$id", CellGrid.serializer(), force, blobs) { Parsers.grid(api.grid(id)) }
    override fun strategies(id: String, force: Boolean) =
        cached("strategies/$id", StrategiesDto.serializer(), force) { api.strategies(id) }.map { s -> s.map { it.items } }

    override fun outlook(id: String, force: Boolean) = cached("outlook/$id", OutlookDto.serializer(), force) { api.outlook(id) }
    override fun openet(id: String, force: Boolean) = cached("openet/$id", OpenEtDto.serializer(), force) { api.openet(id) }
    override fun waterSeen(id: String, force: Boolean) = cached("water_seen/$id", WaterSeenDto.serializer(), force) { api.waterSeen(id) }
    override fun stress(id: String, force: Boolean) = cached("stress/$id", StressDto.serializer(), force) { api.stress(id) }
    override fun insurance(id: String, force: Boolean) = cached("insurance/$id", InsuranceDto.serializer(), force) { api.insurance(id) }
    override fun glossary(force: Boolean) = cached("glossary", GlossaryDto.serializer(), force) { api.glossary() }

    override fun iss(id: String) = cached("iss/$id", IssPhoto.serializer().nullable, false) {
        val j = api.file("${webBase}iss/$id/iss.json")
        val loc = api.location(id)
        val credit = (j["credit"] as? JsonPrimitive)?.contentOrNull.orEmpty()
        j["photos"]?.jsonArray.orEmpty().mapNotNull { e ->
            val p = e.jsonObject
            fun s(k: String) = (p[k] as? JsonPrimitive)?.contentOrNull
            fun d(k: String) = (p[k] as? JsonPrimitive)?.doubleOrNull
            val lat = d("center_lat") ?: return@mapNotNull null; val lon = d("center_lon") ?: return@mapNotNull null
            val miles = hypot((lat - loc.centroid.lat) * 69, (lon - loc.centroid.lon) * 69 * cos(Math.toRadians(loc.centroid.lat)))
            IssPhoto(s("photo_id").orEmpty(), s("date").orEmpty(), s("features").orEmpty(), s("page_url").orEmpty(), "${webBase}iss/$id/${s("file")}", miles, credit)
        }.minByOrNull { it.miles }
    }

    override fun score(id: String, limitAfAc: Double, weights: Map<String, Double>?, scenario: ScenarioDto?): Flow<LoadState<List<StrategyDto>>> {
        val w = weights?.toSortedMap()?.entries?.joinToString(",") { "${it.key}=${it.value}" }.orEmpty()
        val key = "score/$id/${String.format(Locale.US, "%.2f", limitAfAc)}/$w/${scenario?.dTc ?: 0.0}/${scenario?.dPPct ?: 0.0}"
        return cached(key, ListSerializer(StrategyDto.serializer()), force = false) {
            api.score(id, ScoreRequestDto(limitAfAc, weights, scenario)).items
        }
    }

    override fun waterLimit(id: String): Flow<Double?> = prefs.waterLimit(id)
    override suspend fun setWaterLimit(id: String, acreFeetPerAcre: Double) = prefs.setWaterLimit(id, acreFeetPerAcre)

    /** A route that may not exist for this field yet (404) or may fail: null instead of an error. */
    private suspend fun <T> optional(block: suspend () -> T): T? = try { block() } catch (e: CancellationException) { throw e } catch (e: Exception) { null }

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
        store: CacheDao = dao,
        fetch: suspend () -> T,
    ): Flow<LoadState<T>> = channelFlow {
        val saved = store.get(key)?.let { row ->
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
                CachedResponseEntity(key, json.encodeToString(serializer, value), clock.millis()).also { store.put(it) }
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

    /** One network request per key at a time: several panels asking for the same field share one call. */
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
