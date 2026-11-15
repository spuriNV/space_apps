package app.croplytics.testing

import app.croplytics.data.remote.dto.CalendarDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.LocationsDto
import app.croplytics.data.remote.dto.NasaNowDto
import app.croplytics.data.remote.dto.OutlookDto
import app.croplytics.data.remote.dto.ScoreResponseDto
import app.croplytics.data.remote.dto.StrategiesDto
import kotlinx.serialization.json.Json

/** Real API payloads (trimmed) saved from https://croplytics-app.onrender.com/api on 14 Nov 2026. */
object Fixtures {
    val json = Json { ignoreUnknownKeys = true; coerceInputValues = true; explicitNulls = false; isLenient = true }

    fun text(name: String): String = checkNotNull(javaClass.classLoader!!.getResource("fixtures/$name")) { "missing fixture $name" }.readText()

    val location: LocationDto by lazy { json.decodeFromString(text("location_car.json")) }
    val locations: LocationsDto by lazy { json.decodeFromString(text("locations.json")) }
    val calendar: CalendarDto by lazy { json.decodeFromString(text("calendar_car.json")) }
    val nasaNow: NasaNowDto by lazy { json.decodeFromString(text("nasa_now_car.json")) }
    val outlook: OutlookDto by lazy { json.decodeFromString(text("outlook_car.json")) }
    val strategies: StrategiesDto by lazy { json.decodeFromString(text("strategies_car.json")) }
    /** POST /score with a 3.0 acre-ft/acre limit. */
    val scored3: ScoreResponseDto by lazy { json.decodeFromString(text("score_car_3.json")) }
}
