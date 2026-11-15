package app.croplytics.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonPrimitive

/**
 * DTOs mirror the API payloads (backend/api/README.md, the JSON Schemas in schemas/). Every field is
 * optional with a default: the API is still growing (14 fields are being added) and a missing
 * value must show as "not available", never crash the app.
 */

@Serializable
data class SourceDto(
    val id: String? = null,
    val title: String? = null,
    val url: String? = null,
    val verified: Boolean? = null,
)

/** spec B3 SourcedNumber: a value with its range, unit, method and source. */
@Serializable
data class SourcedNumberDto(
    val value: Double? = null,
    val unit: String? = null,
    val low: Double? = null,
    val high: Double? = null,
    val method: String? = null,
    val note: String? = null,
    val source: SourceDto? = null,
    val blocked: Boolean? = null,
) {
    val usable: Double? get() = if (blocked == true) null else value
}

@Serializable
data class LocationsDto(val items: List<LocationDto> = emptyList())

@Serializable
data class LatLonDto(val lon: Double = 0.0, val lat: Double = 0.0)

/** GeoJSON geometry; Polygon or MultiPolygon. Coordinates kept raw and read by [rings]. */
@Serializable
data class GeometryDto(val type: String = "Polygon", val coordinates: JsonElement? = null) {
    /** Outer rings as (lon, lat) pairs. */
    fun rings(): List<List<Pair<Double, Double>>> {
        val c = coordinates as? JsonArray ?: return emptyList()
        fun ring(e: JsonElement): List<Pair<Double, Double>> = (e as? JsonArray).orEmpty().mapNotNull { p ->
            val a = p as? JsonArray ?: return@mapNotNull null
            val lon = a.getOrNull(0)?.jsonPrimitive?.doubleOrNull
            val lat = a.getOrNull(1)?.jsonPrimitive?.doubleOrNull
            if (lon != null && lat != null) lon to lat else null
        }
        return when (type) {
            "MultiPolygon" -> c.mapNotNull { poly -> (poly as? JsonArray)?.firstOrNull()?.let(::ring) }
            else -> listOfNotNull(c.firstOrNull()?.let(::ring))
        }.filter { it.size >= 3 }
    }
}

@Serializable
data class SoilDto(
    val muname: String? = null,
    @SerialName("drainage_class") val drainageClass: String? = null,
    @SerialName("hydrologic_group") val hydrologicGroup: String? = null,
    @SerialName("awc_mm_per_m") val awcMmPerM: SourcedNumberDto? = null,
    @SerialName("om_pct") val omPct: SourcedNumberDto? = null,
    @SerialName("texture_class") val textureClass: String? = null,
    @SerialName("ec_ds_per_m") val ecDsPerM: Double? = null,
    @SerialName("texture_detail") val textureDetail: TextureDetailDto? = null,
)

@Serializable
data class TextureDetailDto(
    @SerialName("sand_pct") val sandPct: Double? = null,
    @SerialName("silt_pct") val siltPct: Double? = null,
    @SerialName("clay_pct") val clayPct: Double? = null,
)

@Serializable
data class TerrainDto(
    @SerialName("slope_mean_pct") val slopeMeanPct: SourcedNumberDto? = null,
    @SerialName("slope_p90_pct") val slopeP90Pct: SourcedNumberDto? = null,
    @SerialName("low_spot_fraction") val lowSpotFraction: SourcedNumberDto? = null,
    @SerialName("elev_m") val elevM: SourcedNumberDto? = null,
)

@Serializable
data class DataGapDto(val id: String = "", val what: String = "", val reason: String = "", @SerialName("filled_with") val filledWith: String? = null)

@Serializable
data class WaterOrderDto(val date: String = "", val kind: String? = null, val title: String = "", val url: String? = null, val licences: Int? = null, val effective: String? = null)

@Serializable
data class WaterContextDto(val watershed: String = "", val orders: List<WaterOrderDto> = emptyList(), val note: String? = null)

@Serializable
data class FirstNationsSummaryDto(
    val statement: String = "",
    @SerialName("field_on_reserve") val fieldOnReserve: Boolean = false,
    @SerialName("nearest_km") val nearestKm: Double? = null,
    @SerialName("nearest_nation") val nearestNation: String? = null,
    /** A name here; an object on the full route. */
    @SerialName("lower_river_nation") val lowerRiverNation: JsonElement? = null,
)

@Serializable
data class DatasetStatusDto(val status: String? = null, val reason: String? = null)

@Serializable
data class SgmaStatusDto(val text: String? = null, val url: String? = null, val verified: Boolean? = null)

@Serializable
data class AllocationInputDto(val value: Double? = null, val unit: String? = null)

@Serializable
data class WaterDto(
    val source: String? = null,
    @SerialName("allocation_input") val allocationInput: AllocationInputDto? = null,
    val district: String? = null,
    @SerialName("sgma_subbasin") val sgmaSubbasin: String? = null,
    @SerialName("sgma_status") val sgmaStatus: SgmaStatusDto? = null,
    /** An object ({looked_up, ...}) or a flag, depending on the API version: kept raw. */
    val lookup: JsonElement? = null,
    val verified: JsonElement? = null,
    /** BC: why the water source is not known. */
    @SerialName("source_note") val sourceNote: String? = null,
) {
    /** The district / GSA was looked up (not the project brief's placeholder). */
    val lookedUp: Boolean get() = (lookup != null && lookup !is kotlinx.serialization.json.JsonNull && (lookup as? JsonPrimitive)?.contentOrNull != "false") ||
        (district != null && !district.contains("(U)"))
    val unverified: Boolean get() = (verified as? JsonPrimitive)?.contentOrNull == "false"
}

@Serializable
data class StationDto(
    val network: String? = null,
    val id: String? = null,
    val name: String? = null,
    @SerialName("distance_km") val distanceKm: Double? = null,
)

@Serializable
data class NasaDatasetDto(
    val id: String = "",
    val name: String = "",
    @SerialName("tells_you") val tellsYou: String? = null,
    val resolution: String? = null,
    @SerialName("date_range") val dateRange: List<String?>? = null,
    val status: String? = null,
    @SerialName("source_url") val sourceUrl: String? = null,
    val note: String? = null,
)

@Serializable
data class FieldEventDto(
    val date: String = "",
    val type: String? = null,
    val title: String = "",
    /** One or two words for the timeline buttons ("2022 drought"). */
    val short: String? = null,
    val url: String? = null,
    val verified: Boolean? = null,
    val detail: String? = null,
    @SerialName("end_date") val endDate: String? = null,
)

@Serializable
data class LocationDto(
    val id: String,
    val name: String = "",
    @SerialName("farmer_name") val farmerName: String? = null,
    /** Newer payloads carry `county` as `{fips, name}`; older ones only `county_fips`. */
    val county: JsonElement? = null,
    @SerialName("county_fips") val countyFips: String? = null,
    @SerialName("county_name") val countyNameApi: String? = null,
    /** Crop family ("rice", "forage") from the field registry. */
    val family: String? = null,
    /** "ca" (default) or "bc". */
    val region: String? = null,
    /** Backend fetch status per dataset (`datasets.<id>.status`), for the NASA list. */
    val datasets: Map<String, DatasetStatusDto> = emptyMap(),
    @SerialName("market_preference") val marketPreference: String? = null,
    val acres: Double? = null,
    val geometry: GeometryDto? = null,
    val centroid: LatLonDto = LatLonDto(),
    @SerialName("area_ha") val areaHa: SourcedNumberDto? = null,
    @SerialName("dwr_unique_id") val dwrUniqueId: String? = null,
    val soil: SoilDto? = null,
    val terrain: TerrainDto? = null,
    val water: WaterDto? = null,
    val stations: List<StationDto> = emptyList(),
    @SerialName("nasa_datasets") val nasaDatasets: List<NasaDatasetDto> = emptyList(),
    @SerialName("crop_history") val cropHistory: Map<String, String> = emptyMap(),
    val events: List<FieldEventDto> = emptyList(),
    /** BC: California datasets this field lacks, why, and what fills the gap. */
    @SerialName("data_gaps") val dataGaps: List<DataGapDto> = emptyList(),
    /** BC: the watershed and the Province's irrigation orders, in place of a water district. */
    @SerialName("water_context") val waterContext: WaterContextDto? = null,
    /** BC: the First Nations summary; the full card comes from GET .../first_nations. */
    @SerialName("first_nations") val firstNations: FirstNationsSummaryDto? = null,
) {
    val isBC: Boolean get() = region == "bc"
    fun gap(id: String): DataGapDto? = if (isBC) dataGaps.firstOrNull { it.id == id } else null

    /** County name from `county` (string or object), else null. */
    val countyName: String?
        get() = countyNameApi ?: when (val c = county) {
            is JsonPrimitive -> c.contentOrNull
            is JsonObject -> (c["name"] as? JsonPrimitive)?.contentOrNull
            else -> null
        }
}
