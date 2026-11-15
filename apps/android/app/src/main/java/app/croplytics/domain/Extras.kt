package app.croplytics.domain

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import java.time.LocalDate
import java.time.format.TextStyle
import java.util.Locale
import kotlin.math.roundToInt

// ---------- "This week" (GET /locations/{id}/this_week, ThisWeek.tsx) ----------

data class WeekDay(val dow: String, val rainIn: Double?, val hiF: Int?, val loF: Int?)
data class NeedDay(val dow: String, val needIn: Double)
data class AccessDay(val dow: String, val status: String, val word: String, val name: String, val why: String)
data class WeekAlert(val title: String, val url: String)

data class WeekView(
    val label: String,
    val verdict: String,
    /** "irrigate", "flooded", "rain_covers" ... */
    val kind: String,
    val acreInPerAcre: Double?,
    val need: List<NeedDay>,
    val accessLine: String,
    val access: List<AccessDay>,
    val forecast: List<WeekDay>,
    val alerts: List<WeekAlert>,
    val irrigationTag: String,
    val accessTag: String,
    val forecastTag: String,
) {
    val hasAnything get() = verdict.isNotBlank() || access.isNotEmpty() || forecast.isNotEmpty() || alerts.isNotEmpty()
}

object WeekLogic {
    /** Inches as the web shows them: 0 below 0.05, one decimal below 10, else whole. */
    fun inches(mm: Double): String { val n = mm / 25.4; return if (n < 0.05) "0" else if (n < 10) String.format(Locale.US, "%.1f", n) else n.roundToInt().toString() }
    fun degF(c: Double) = (c * 1.8 + 32).roundToInt()

    private fun obj(e: JsonElement?) = e as? JsonObject
    private fun str(o: JsonObject?, k: String) = (o?.get(k) as? JsonPrimitive)?.contentOrNull
    private fun num(e: JsonElement?): Double? = ((e as? JsonObject)?.get("value") as? JsonPrimitive)?.doubleOrNull
    private fun arr(o: JsonObject?, k: String) = (o?.get(k) as? JsonArray).orEmpty().mapNotNull { it as? JsonObject }
    private fun dow(date: String?) = runCatching { LocalDate.parse(date).dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.US) }.getOrDefault("")

    /** A section is shown unless it is unavailable or not applicable (a missing `sections` entry also hides it). */
    private fun show(sec: JsonObject?, key: String): Boolean { val s = str(obj(sec?.get(key)), "status"); return s != null && s != "unavailable" && s != "not_applicable" }
    private fun tag(sec: JsonObject?, key: String) = when (str(obj(sec?.get(key)), "status")) { "fallback" -> "From a backup forecast."; "partial" -> "Partly available."; else -> "" }

    fun parse(j: JsonObject): WeekView {
        val sec = obj(j["sections"])
        val irr = obj(j["irrigation"]); val acc = obj(j["field_access"])
        val showIrr = show(sec, "irrigation"); val showAcc = show(sec, "field_access"); val showFc = show(sec, "forecast"); val showAl = show(sec, "alerts")
        val kind = str(irr, "kind").orEmpty()
        val days = arr(irr, "days")
        val needs = days.map { num(it["need_mm"]) }
        val need = if (showIrr && kind == "irrigate" && needs.any { it != null }) days.mapIndexed { i, d -> NeedDay(dow(str(d, "date")), (needs[i] ?: 0.0) / 25.4) } else emptyList()
        val access = if (showAcc) arr(acc, "days").map { d ->
            val st = str(d, "status") ?: "unknown"
            AccessDay(dow(str(d, "date")), st, when (st) { "ok" -> "OK"; "marginal" -> "Maybe"; "too_wet" -> "Wet"; else -> "–" },
                when (st) { "ok" -> "OK to work"; "marginal" -> "Marginal"; "too_wet" -> "Too wet to work"; else -> "Unknown" },
                (d["why"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.contentOrNull }.joinToString(" "))
        }.takeIf { l -> l.any { it.status != "unknown" } }.orEmpty() else emptyList()
        val fc = if (showFc) arr(j, "forecast").map { d ->
            WeekDay(str(d, "weekday") ?: dow(str(d, "date")), num(d["rain_mm"])?.let { it / 25.4 }, num(d["tmax_c"])?.let(::degF), num(d["tmin_c"])?.let(::degF))
        } else emptyList()
        val alerts = if (showAl) arr(j, "alerts").map { a ->
            val area = str(a, "area")?.substringBefore(";")
            WeekAlert((str(a, "event") ?: str(a, "headline") ?: "Weather alert") + (area?.let { " · $it" } ?: ""), str(a, "url")?.takeIf { it.startsWith("http") } ?: "https://www.weather.gov/")
        } else emptyList()
        return WeekView(
            str(j, "label").orEmpty(), if (showIrr) str(irr, "verdict").orEmpty() else "", kind, num(irr?.get("acre_in_per_acre")), need,
            if (access.isNotEmpty()) str(acc, "line").orEmpty() else "", access, fc, alerts, tag(sec, "irrigation"), tag(sec, "field_access"), tag(sec, "forecast"),
        )
    }
}

// ---------- Farm catalog (GET /catalog) ----------

data class CatalogPin(val id: String, val name: String, val lat: Double, val lon: Double, val group: String, val groupLabel: String, val acres: Double?, val county: String)
data class CropGroup(val key: String, val label: String, val count: Int)
data class Catalog(val pins: List<CatalogPin>, val groups: List<CropGroup>)

object CatalogLogic {
    /** Colour-blind-safe tones that read on imagery (the web's GROUP_COLOR). */
    val colors = mapOf(
        "grapes" to "#CC79A7", "forage" to "#009E73", "vegetables" to "#D55E00", "nuts" to "#8c6d1f", "grain" to "#E69F00", "rice" to "#0072B2",
        "citrus" to "#F0E442", "cotton" to "#9a9a9a", "orchard" to "#56B4E9", "canola" to "#4d4d4d", "soy" to "#7a9a2e", "peanuts" to "#a65c3a",
        "potatoes" to "#c9a46b", "hops" to "#2e8f5f", "sorghum" to "#8f3b6e", "pulses" to "#3b6fb0",
    )
    fun color(group: String) = colors[group] ?: "#8a8a80"
    /** One letter per crop group, so colour is never the only cue. */
    private val letters = mapOf("grapes" to "G", "forage" to "F", "vegetables" to "V", "nuts" to "N", "grain" to "A", "rice" to "R", "citrus" to "C", "cotton" to "T", "orchard" to "O", "canola" to "K", "soy" to "S", "peanuts" to "P", "potatoes" to "U", "hops" to "H", "sorghum" to "Y", "pulses" to "L")
    fun letter(group: String) = letters[group] ?: group.take(1).uppercase()

    fun parse(j: JsonObject): Catalog {
        fun s(o: JsonObject, k: String) = (o[k] as? JsonPrimitive)?.contentOrNull
        fun d(o: JsonObject, k: String) = (o[k] as? JsonPrimitive)?.doubleOrNull
        val pins = (j["items"] as? JsonArray).orEmpty().mapNotNull { e ->
            val o = e as? JsonObject ?: return@mapNotNull null
            CatalogPin(s(o, "id") ?: return@mapNotNull null, s(o, "name").orEmpty(), d(o, "lat") ?: return@mapNotNull null, d(o, "lon") ?: return@mapNotNull null,
                s(o, "crop_group").orEmpty(), s(o, "crop_group_label").orEmpty(), d(o, "acres"), s(o, "county").orEmpty())
        }
        val groups = (j["crop_groups"] as? JsonObject).orEmpty().mapNotNull { (k, v) ->
            val o = v as? JsonObject ?: return@mapNotNull null
            CropGroup(k, s(o, "label") ?: k, d(o, "count")?.toInt() ?: 0)
        }.sortedByDescending { it.count }
        return Catalog(pins, groups)
    }
}

/** Ring of tapped points (lon, lat) to a closed GeoJSON Polygon body for POST /my-fields. */
object DrawLogic {
    fun closed(points: List<Pair<Double, Double>>): List<Pair<Double, Double>> = if (points.size < 3) points else points + points.first()
    /** Rough area in acres (equirectangular about the ring's own latitude). */
    fun acres(points: List<Pair<Double, Double>>): Double {
        if (points.size < 3) return 0.0
        val lat0 = Math.toRadians(points.map { it.second }.average()); val r = 6371008.8
        var a = 0.0
        for (i in points.indices) {
            val (x1, y1) = points[i]; val (x2, y2) = points[(i + 1) % points.size]
            a += Math.toRadians(x1) * Math.cos(lat0) * r * Math.toRadians(y2) * r - Math.toRadians(x2) * Math.cos(lat0) * r * Math.toRadians(y1) * r
        }
        return Math.abs(a) / 2 / 4046.8564224
    }
}
