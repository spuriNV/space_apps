package app.croplytics.data.remote

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
import app.croplytics.data.remote.dto.ScoreResponseDto
import app.croplytics.data.remote.dto.StrategiesDto
import app.croplytics.data.remote.dto.StressDto
import app.croplytics.data.remote.dto.WaterSeenDto
import kotlinx.serialization.json.JsonObject
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Url

/** The CropLytics API (backend/api), the same routes the web app reads (frontend/app/src/api.ts). Base URL ends in `/api/`. */
interface CropLyticsApi {
    @GET("locations")
    suspend fun locations(): LocationsDto

    @GET("locations/{id}")
    suspend fun location(@Path("id") id: String): LocationDto

    /** source = "hls" for the NASA-native calendar; the web uses it first when served. */
    @GET("locations/{id}/calendar")
    suspend fun calendar(@Path("id") id: String, @Query("source") source: String? = null): CalendarDto

    @GET("locations/{id}/calendar_ml")
    suspend fun calendarMl(@Path("id") id: String): CalendarDto

    @GET("locations/{id}/nasa_now")
    suspend fun nasaNow(@Path("id") id: String): NasaNowDto

    /** One row per 10-day step from 2015: SMAP / GRACE-FO percentiles, IMERG rain, OPERA water, HLS greenness. */
    @GET("locations/{id}/nasa_series")
    suspend fun nasaSeries(@Path("id") id: String): JsonObject

    /** The daily record (about 2 MB): parsed straight into the compact model. */
    @GET("locations/{id}/daily")
    suspend fun daily(@Path("id") id: String): JsonObject

    /** The 30 m grid with greenness per quarter and per clear scene (about 2 MB). */
    @GET("locations/{id}/grid")
    suspend fun grid(@Path("id") id: String): JsonObject

    @GET("locations/{id}/strategies")
    suspend fun strategies(@Path("id") id: String): StrategiesDto

    @POST("locations/{id}/score")
    suspend fun score(@Path("id") id: String, @Body body: ScoreRequestDto): ScoreResponseDto

    @GET("locations/{id}/outlook")
    suspend fun outlook(@Path("id") id: String): OutlookDto

    @GET("locations/{id}/models")
    suspend fun models(@Path("id") id: String): ModelsDto

    @GET("locations/{id}/openet")
    suspend fun openet(@Path("id") id: String): OpenEtDto

    @GET("locations/{id}/water_seen")
    suspend fun waterSeen(@Path("id") id: String): WaterSeenDto

    @GET("locations/{id}/stress")
    suspend fun stress(@Path("id") id: String): StressDto

    @GET("locations/{id}/insurance")
    suspend fun insurance(@Path("id") id: String): InsuranceDto

    /** BC fields: the First Nations card (404 for California fields). */
    @GET("locations/{id}/first_nations")
    suspend fun firstNations(@Path("id") id: String): app.croplytics.data.remote.dto.FirstNationsDto

    @GET("locations/{id}/first_nations/reserves.geojson")
    suspend fun reserves(@Path("id") id: String): JsonObject

    @GET("glossary")
    suspend fun glossary(): GlossaryDto

    /** Files the web app serves next to the API (ISS photo index under /iss/<id>/iss.json). */
    @GET
    suspend fun file(@Url url: String): JsonObject
}
