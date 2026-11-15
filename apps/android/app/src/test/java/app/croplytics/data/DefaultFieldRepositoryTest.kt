package app.croplytics.data

import app.cash.turbine.test
import app.croplytics.data.local.CacheDao
import app.croplytics.data.local.CachedResponseEntity
import app.croplytics.data.local.FieldPrefs
import app.croplytics.data.remote.CropLyticsApi
import app.croplytics.data.repository.DefaultFieldRepository
import app.croplytics.data.repository.LoadError
import app.croplytics.data.repository.LoadState
import app.croplytics.data.repository.RepositoryConfig
import app.croplytics.testing.Fixtures
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.time.Clock
import java.time.Instant
import java.time.ZoneOffset
import java.util.concurrent.TimeUnit

class DefaultFieldRepositoryTest {
    private lateinit var server: MockWebServer
    private lateinit var dao: InMemoryCacheDao
    private lateinit var scope: CoroutineScope
    private val now = Instant.parse("2026-11-14T20:00:00Z")
    private val clock = Clock.fixed(now, ZoneOffset.UTC)

    private class InMemoryCacheDao : CacheDao {
        val rows = mutableMapOf<String, CachedResponseEntity>()
        override suspend fun get(key: String) = rows[key]
        override suspend fun put(entity: CachedResponseEntity) { rows[entity.key] = entity }
    }

    private class InMemoryPrefs : FieldPrefs {
        val limits = MutableStateFlow<Map<String, Double>>(emptyMap())
        override fun waterLimit(fieldId: String): Flow<Double?> = limits.map { it[fieldId] }
        override suspend fun setWaterLimit(fieldId: String, acreFeetPerAcre: Double) { limits.value = limits.value + (fieldId to acreFeetPerAcre) }
    }

    @Before
    fun setUp() {
        server = MockWebServer().apply { start() }
        dao = InMemoryCacheDao()
        scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    }

    @After
    fun tearDown() {
        scope.cancel()
        server.shutdown()
    }

    private val blobs = InMemoryCacheDao()

    private fun repo(config: RepositoryConfig = RepositoryConfig(wakeAfterMs = 2_000)) = DefaultFieldRepository(
        api = Retrofit.Builder()
            .baseUrl(server.url("/api/"))
            .client(OkHttpClient.Builder().readTimeout(5, TimeUnit.SECONDS).build())
            .addConverterFactory(Fixtures.json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(CropLyticsApi::class.java),
        dao = dao,
        prefs = InMemoryPrefs(),
        json = Fixtures.json,
        appScope = scope,
        clock = clock,
        config = config,
        blobs = blobs,
    )

    private fun ok(name: String) = MockResponse().setResponseCode(200).setBody(Fixtures.text(name))

    @Test
    fun `first load fetches, shows the data and saves it on the phone`() = runBlocking {
        server.enqueue(ok("location_car.json"))
        repo().location("car_colusa_rice").test {
            assertEquals(LoadState.Loading, awaitItem())
            val ready = awaitItem() as LoadState.Ready
            assertEquals("car_colusa_rice", ready.data.id)
            assertEquals(false, ready.offline)
            awaitComplete()
        }
        assertEquals("/api/locations/car_colusa_rice", server.takeRequest().path)
        assertTrue(dao.rows.containsKey("location/car_colusa_rice"))
    }

    @Test
    fun `a fresh saved copy is shown without asking the server`() = runBlocking {
        dao.put(CachedResponseEntity("location/car_colusa_rice", Fixtures.text("location_car.json"), now.toEpochMilli() - 60_000))
        val first = repo().location("car_colusa_rice").first()
        assertTrue(first is LoadState.Ready)
        assertEquals(0, server.requestCount)
    }

    @Test
    fun `an old saved copy shows first, then the server's answer replaces it`() = runBlocking {
        dao.put(CachedResponseEntity("location/car_colusa_rice", Fixtures.text("location_car.json"), now.toEpochMilli() - 86_400_000))
        server.enqueue(ok("location_car.json"))
        repo().location("car_colusa_rice").test {
            val saved = awaitItem() as LoadState.Ready
            assertTrue(saved.refreshing)
            assertEquals(now.minusSeconds(86_400), saved.savedAt)
            val fresh = awaitItem() as LoadState.Ready
            assertEquals(false, fresh.refreshing)
            assertEquals(now, fresh.savedAt)
            awaitComplete()
        }
    }

    @Test
    fun `offline with a saved copy keeps it and says when it was saved`() = runBlocking {
        val savedAt = now.toEpochMilli() - 86_400_000
        dao.put(CachedResponseEntity("location/car_colusa_rice", Fixtures.text("location_car.json"), savedAt))
        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AT_START))
        repo().location("car_colusa_rice").test {
            assertTrue((awaitItem() as LoadState.Ready).refreshing)
            val offline = awaitItem() as LoadState.Ready
            assertTrue(offline.offline)
            assertEquals(Instant.ofEpochMilli(savedAt), offline.savedAt)
            awaitComplete()
        }
    }

    @Test
    fun `a missing route is reported as not available, a server error as server`() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(404).setBody("""{"detail":"not found"}"""))
        assertEquals(LoadState.Failed(LoadError.NotAvailable), repo().stress("car_colusa_rice").first { it is LoadState.Failed })
        server.enqueue(MockResponse().setResponseCode(502))
        assertEquals(LoadState.Failed(LoadError.Server), repo().waterSeen("car_colusa_rice").first { it is LoadState.Failed })
    }

    @Test
    fun `a slow server with nothing saved shows the waking state`() = runBlocking {
        server.enqueue(ok("nasa_now_car.json").setHeadersDelay(800, TimeUnit.MILLISECONDS))
        repo(RepositoryConfig(wakeAfterMs = 100)).nasaNow("car_colusa_rice").test(timeout = kotlin.time.Duration.parse("5s")) {
            assertEquals(LoadState.Loading, awaitItem())
            assertEquals(LoadState.Waking, awaitItem())
            assertTrue(awaitItem() is LoadState.Ready)
            awaitComplete()
        }
    }

    @Test
    fun `two screens asking for the same field share one request`() = runBlocking {
        server.enqueue(ok("strategies_car.json").setHeadersDelay(300, TimeUnit.MILLISECONDS))
        val r = repo()
        val a = async { r.strategies("car_colusa_rice").first { it is LoadState.Ready } }
        val b = async { r.strategies("car_colusa_rice").first { it is LoadState.Ready } }
        assertEquals(4, (a.await() as LoadState.Ready).data.size)
        assertEquals(4, (b.await() as LoadState.Ready).data.size)
        assertEquals(1, server.requestCount)
    }

    @Test
    fun `scoring posts the water limit and caches per limit`() = runBlocking {
        server.enqueue(ok("score_car_3.json"))
        val r = repo()
        val scored = r.score("car_colusa_rice", 3.0).first { it is LoadState.Ready } as LoadState.Ready
        assertEquals("car2_dryyear_safflower", scored.data.maxBy { it.composite.value ?: 0.0 }.id)
        val req = server.takeRequest()
        assertEquals("POST", req.method)
        assertEquals("""{"allocation":3.0}""", req.body.readUtf8())
        assertTrue(dao.rows.keys.any { it.startsWith("score/car_colusa_rice/3.00/") })
    }

    @Test
    fun `the calendar falls back to Landsat and Sentinel-2 when HLS is not served, with the ML comparison`() = runBlocking {
        server.dispatcher = object : okhttp3.mockwebserver.Dispatcher() {
            override fun dispatch(request: okhttp3.mockwebserver.RecordedRequest): MockResponse = when {
                request.path!!.contains("calendar?source=hls") -> MockResponse().setResponseCode(404)
                request.path!!.endsWith("/calendar") -> ok("calendar_car.json")
                request.path!!.endsWith("/calendar_ml") -> ok("calendar_ml_car.json")
                request.path!!.endsWith("/models") -> ok("models_car.json")
                else -> MockResponse().setResponseCode(404)
            }
        }
        val b = (repo().calendar("car_colusa_rice").first { it is LoadState.Ready } as LoadState.Ready).data
        assertEquals(false, b.calendar.hls)
        assertTrue(b.calendar.hasMl)
        assertEquals((2016..2026).toList(), b.calendar.years.map { it.year })
        assertTrue(b.calendar.year(2026)!!.rule.any { it != 'u' })
        assertEquals("random forest", b.ml!!.model)
    }

    @Test
    fun `the daily record is parsed small and kept in the file store, not Room`() = runBlocking {
        server.enqueue(ok("daily_car.json"))
        val d = (repo().daily("car_colusa_rice").first { it is LoadState.Ready } as LoadState.Ready).data
        assertTrue(d.dates.size > 1000)
        assertTrue(blobs.rows.containsKey("daily/car_colusa_rice"))
        assertTrue(!dao.rows.containsKey("daily/car_colusa_rice"))
    }
}
