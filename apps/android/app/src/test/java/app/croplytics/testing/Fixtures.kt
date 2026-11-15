package app.croplytics.testing

import app.croplytics.data.remote.dto.CalendarDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.LocationsDto
import app.croplytics.data.remote.dto.ModelsDto
import app.croplytics.data.remote.dto.NasaNowDto
import app.croplytics.data.remote.dto.OutlookDto
import app.croplytics.data.remote.dto.ScoreResponseDto
import app.croplytics.data.remote.dto.StrategiesDto
import app.croplytics.domain.Calendars
import app.croplytics.domain.CellGrid
import app.croplytics.domain.Daily
import app.croplytics.domain.FieldCalendar
import app.croplytics.domain.FieldNames
import app.croplytics.domain.Parsers
import app.croplytics.domain.RegionalSeries
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import java.time.LocalDate

/** Real API payloads (trimmed) saved from https://croplytics-app.onrender.com/api on 14-15 Nov 2026. */
object Fixtures {
    val json = Json { ignoreUnknownKeys = true; coerceInputValues = true; explicitNulls = false; isLenient = true }
    val today: LocalDate = LocalDate.of(2026, 11, 14)
    val years = (2016..2026).toList()

    fun text(name: String): String = checkNotNull(javaClass.classLoader!!.getResource("fixtures/$name")) { "missing fixture $name" }.readText()
    private fun obj(name: String) = json.decodeFromString(JsonObject.serializer(), text(name))

    val location: LocationDto by lazy { json.decodeFromString(text("location_car.json")) }
    val locations: LocationsDto by lazy { json.decodeFromString(text("locations.json")) }
    val calendarDto: CalendarDto by lazy { json.decodeFromString(text("calendar_car.json")) }
    val calendarMlDto: CalendarDto by lazy { json.decodeFromString(text("calendar_ml_car.json")) }
    val models: ModelsDto by lazy { json.decodeFromString(text("models_car.json")) }
    val nasaNow: NasaNowDto by lazy { json.decodeFromString(text("nasa_now_car.json")) }
    val outlook: OutlookDto by lazy { json.decodeFromString(text("outlook_car.json")) }
    val strategies: StrategiesDto by lazy { json.decodeFromString(text("strategies_car.json")) }
    /** POST /score with a 3.0 acre-ft/acre limit. */
    val scored3: ScoreResponseDto by lazy { json.decodeFromString(text("score_car_3.json")) }
    val regional: RegionalSeries by lazy { Parsers.regional(obj("nasa_series_car.json"), years) }
    val daily: Daily by lazy { Parsers.daily(obj("daily_car.json")) }
    val grid: CellGrid by lazy { Parsers.grid(obj("grid_car.json")) }
    val calendar: FieldCalendar by lazy { Calendars.convert(location.id, calendarDto, calendarMlDto, FieldNames.history(location), years, hls = false) }
}
