package app.croplytics.domain

import app.croplytics.data.remote.dto.DataGapDto
import app.croplytics.data.remote.dto.InsuranceDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.remote.dto.WaterOrderDto
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlin.math.roundToInt

/** British Columbia and region wording (web: lib.ts RAIN_FED, shared.tsx orderText / GapLine, FirstNations.tsx). */
object BcLogic {
    const val RAIN_FED = "Rain-fed (no irrigation)"

    /** A rotation that is never irrigated (every calendar year irrigated = false), e.g. BC sainfoin-grass. */
    fun rainFed(s: StrategyDto?): Boolean = s != null && s.calendar.isNotEmpty() && s.calendar.all { it.irrigated == false }

    fun stationsName(loc: LocationDto) = if (loc.isBC) "Environment Canada (ECCC) weather stations near the field" else "NOAA weather stations near the field"
    fun cropMapName(loc: LocationDto) = if (loc.isBC) "AAFC Annual Crop Inventory (Agriculture Canada)" else "USDA Cropland Data Layer"
    fun cropMapShort(loc: LocationDto) = if (loc.isBC) "AAFC" else "USDA"

    /** One BC order in a few words: an order to stop irrigating (with its licence count) or a rescission. */
    fun orderText(o: WaterOrderDto) = if (o.kind == "rescission") "order rescinded"
        else "order to stop irrigating forage${o.licences?.let { " ($it licences)" } ?: ""}${o.effective?.takeIf { it != o.date }?.let { ", from ${Timeline.fmtDate(it)}" } ?: ""}"

    /** "Not available in BC. <reason>" where the route still 404s; otherwise the reason and what fills the gap (More detail). */
    fun gapLine(g: DataGapDto?, missing: Boolean): String? = g?.let {
        if (missing) "Not available in BC. ${it.reason}"
        else "${it.reason}${it.filledWith?.let { f -> " ${f.replaceFirstChar(Char::uppercase)}${if (f.endsWith(".")) "" else "."}" } ?: ""}"
    }

    /** "SALMON RIVER 1 (SPLATSIN)" -> "Salmon River 1 (Splatsin)". */
    fun reserveName(s: String) = s.lowercase().replace(Regex("(^|[\\s(])(\\p{L})")) { m -> m.groupValues[1] + m.groupValues[2].uppercase() }

    private val CAUSE = mapOf("drought" to "drought", "excess_moisture" to "too much water", "heat" to "heat", "other" to "frost and other", "frost_other" to "frost and other", "frost" to "frost", "cold" to "cold")

    /** Loss shares when there are no dollar figures (BC estimate from station history). */
    fun lossShares(ins: InsuranceDto?): String? {
        val p = ins?.profiles?.values?.firstOrNull() ?: return null
        if (p.totalIndemnityUsd != null) return null
        val shares = p.shares.filterKeys { it.startsWith("share_") }.mapNotNull { (k, v) -> v.value?.takeIf { it > 0 }?.let { k.removePrefix("share_") to it } }
        if (shares.isEmpty()) return null
        return "Usual causes of crop loss here: ${shares.joinToString(", ") { (c, s) -> "${CAUSE[c] ?: c.replace('_', ' ')} ${(s * 100).roundToInt()}%" }}. No dollar figures."
    }
}

/** A reserve outline near a BC field, drawn for context only. */
@Serializable
data class Reserve(val name: String, val nation: String, val km: Double, val rings: List<List<Pair<Double, Double>>>)

fun Parsers.reserveList(body: JsonObject): List<Reserve> = body["features"]?.jsonArray.orEmpty().mapNotNull { f ->
    val o = f as? JsonObject ?: return@mapNotNull null
    val p = o["properties"] as? JsonObject
    val g = o["geometry"] as? JsonObject ?: return@mapNotNull null
    fun ring(e: kotlinx.serialization.json.JsonElement) = (e as? JsonArray).orEmpty().mapNotNull { pt -> (pt as? JsonArray)?.let { (it[0] as JsonPrimitive).doubleOrNull!! to (it[1] as JsonPrimitive).doubleOrNull!! } }
    val c = g["coordinates"] as? JsonArray ?: return@mapNotNull null
    val rings = when ((g["type"] as? JsonPrimitive)?.contentOrNull) {
        "MultiPolygon" -> c.mapNotNull { poly -> (poly as? JsonArray)?.firstOrNull()?.let(::ring) }
        else -> listOfNotNull(c.firstOrNull()?.let(::ring))
    }
    Reserve(
        (p?.get("name") as? JsonPrimitive)?.contentOrNull ?: "Reserve",
        (p?.get("nation") as? JsonPrimitive)?.contentOrNull ?: (p?.get("band") as? JsonPrimitive)?.contentOrNull ?: "",
        (p?.get("distance_to_field_km") as? JsonPrimitive)?.doubleOrNull ?: 99.0, rings,
    )
}
