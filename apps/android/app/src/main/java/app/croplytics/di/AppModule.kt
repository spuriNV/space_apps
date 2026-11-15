package app.croplytics.di

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStoreFile
import androidx.room.Room
import app.croplytics.BuildConfig
import app.croplytics.data.local.CacheDao
import app.croplytics.data.local.CacheDatabase
import app.croplytics.data.local.DataStoreFieldPrefs
import app.croplytics.data.local.FieldPrefs
import app.croplytics.data.remote.CropLyticsApi
import app.croplytics.data.repository.DefaultFieldRepository
import app.croplytics.data.repository.FieldRepository
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.time.Clock
import java.util.concurrent.TimeUnit
import javax.inject.Qualifier
import javax.inject.Singleton

@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class ApplicationScope

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun json(): Json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        explicitNulls = false
        isLenient = true
    }

    /**
     * The free Render server sleeps when idle and takes up to about 50 s to answer the first
     * request, so the read timeout is generous; the UI says "Waking the server" meanwhile.
     */
    @Provides
    @Singleton
    fun okHttp(): OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(75, TimeUnit.SECONDS)
        .callTimeout(90, TimeUnit.SECONDS)
        .apply {
            if (BuildConfig.DEBUG) addInterceptor(HttpLoggingInterceptor().setLevel(HttpLoggingInterceptor.Level.BASIC))
        }
        .build()

    @Provides
    @Singleton
    fun api(client: OkHttpClient, json: Json): CropLyticsApi = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(client)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()
        .create(CropLyticsApi::class.java)

    @Provides
    @Singleton
    fun database(@ApplicationContext context: Context): CacheDatabase =
        Room.databaseBuilder(context, CacheDatabase::class.java, "croplytics-cache.db")
            .fallbackToDestructiveMigration(dropAllTables = true) // it is only a cache
            .build()

    @Provides
    fun cacheDao(db: CacheDatabase): CacheDao = db.cacheDao()

    @Provides
    @Singleton
    fun dataStore(@ApplicationContext context: Context): DataStore<Preferences> =
        PreferenceDataStoreFactory.create { context.preferencesDataStoreFile("field_prefs") }

    @Provides
    @Singleton
    fun fieldPrefs(store: DataStore<Preferences>): FieldPrefs = DataStoreFieldPrefs(store)

    /** "Today" for the screens; tests pass a fixed clock. */
    @Provides
    fun clock(): Clock = Clock.systemDefaultZone()

    @Provides
    @Singleton
    @ApplicationScope
    fun appScope(): CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    @Provides
    @Singleton
    fun repository(
        api: CropLyticsApi,
        dao: CacheDao,
        prefs: FieldPrefs,
        json: Json,
        @ApplicationScope scope: CoroutineScope,
    ): FieldRepository = DefaultFieldRepository(api, dao, prefs, json, scope)
}
