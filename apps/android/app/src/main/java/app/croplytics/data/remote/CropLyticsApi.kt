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
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

/** The CropLytics API (backend/api). Base URL ends in `/api/`. */
interface CropLyticsApi {
    @GET("locations")
    suspend fun locations(): LocationsDto

    @GET("locations/{id}")
    suspend fun location(@Path("id") id: String): LocationDto

    @GET("locations/{id}/calendar")
    suspend fun calendar(@Path("id") id: String): CalendarDto

    @GET("locations/{id}/nasa_now")
    suspend fun nasaNow(@Path("id") id: String): NasaNowDto

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

    @GET("glossary")
    suspend fun glossary(): GlossaryDto
}
