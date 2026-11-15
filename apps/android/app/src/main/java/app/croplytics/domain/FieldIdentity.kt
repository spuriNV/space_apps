package app.croplytics.domain

import app.croplytics.data.remote.dto.LocationDto
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.roundToInt

/** How a grower names a field: "Rice field 3.5 miles east of Williams", 149 acres, Colusa County. */
data class FieldIdentity(
    val id: String,
    val name: String,
    val county: String?,
    val acres: Int?,
    val latestCropYear: Int?,
    val latestCrop: String?,
    val mainCrop: String,
    val recordLine: String,
    val stateFieldNo: String?,
    val lat: Double,
    val lon: Double,
) {
    /** "149 acres, rice in 2025, Colusa County". */
    val subtitle: String
        get() = listOfNotNull(
            acres?.let { "$it acres" },
            if (latestCrop != null && latestCropYear != null) "${latestCrop.lowercase()} in $latestCropYear" else null,
            county?.let { "$it County" },
        ).joinToString(", ")

    /** Searchable text: name, county, crop and IDs. */
    val searchText: String
        get() = listOfNotNull(name, county, latestCrop, mainCrop, stateFieldNo, id).joinToString(" ").lowercase()
}

object FieldNames {
    /** The Cropland Data Layer's own labels are not what a grower says. */
    fun cropName(raw: String?): String {
        val c = raw.orEmpty().replace(Regex("\\s*\\(CDL pending\\)", RegexOption.IGNORE_CASE), "").trim()
        return when {
            c.isEmpty() -> "Not recorded"
            c.startsWith("Fallow") -> "Left fallow"
            c.startsWith("Dbl Crop WinWht/Corn") -> "Wheat, then corn"
            c.startsWith("Dbl Crop ") -> c.removePrefix("Dbl Crop ").replaceFirst("/", ", then ")
            else -> c
        }
    }

    /** Towns growers use as landmarks near the fields (Sacramento Valley, San Joaquin Valley). */
    private val towns = listOf(
        Town("Williams", 39.1546, -122.1494), Town("Colusa", 39.2143, -122.0094), Town("Arbuckle", 39.0174, -122.0578),
        Town("Maxwell", 39.2763, -122.1914), Town("Grimes", 39.0738, -121.8994), Town("Princeton", 39.4049, -122.0108),
        Town("Glenn", 39.5216, -122.0130), Town("Willows", 39.5243, -122.1936), Town("Richvale", 39.4949, -121.7436),
        Town("Biggs", 39.4124, -121.7128), Town("Gridley", 39.3638, -121.6936), Town("Robbins", 38.8724, -121.7063),
        Town("Knights Landing", 38.7999, -121.7183), Town("Zamora", 38.7966, -121.8827), Town("Woodland", 38.6785, -121.7733),
        Town("Dunnigan", 38.8852, -121.9697), Town("Yuba City", 39.1404, -121.6169), Town("Hanford", 36.3275, -119.6457),
        Town("Lemoore", 36.3008, -119.7829), Town("Corcoran", 36.0980, -119.5604), Town("Stratford", 36.1897, -119.8232),
        Town("Goshen", 36.3510, -119.4204), Town("Tipton", 36.0594, -119.3121), Town("Visalia", 36.3302, -119.2921),
        Town("Tulare", 36.2077, -119.3473), Town("Riverdale", 36.4311, -119.8596), Town("Laton", 36.4333, -119.6871),
        Town("El Nido", 37.1335, -120.4893), Town("Merced", 37.3022, -120.4830), Town("Newman", 37.3138, -121.0208),
        Town("Gustine", 37.2577, -120.9988), Town("Los Banos", 37.0583, -120.8499),
    )

    private data class Town(val name: String, val lat: Double, val lon: Double)

    private val directions = listOf("north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest")

    /** "3.5 miles east of Williams" from the field centre; null when no listed town is within ~40 miles. */
    fun nearTown(lat: Double, lon: Double): String? {
        var best: Triple<Town, Double, Pair<Double, Double>>? = null
        for (t in towns) {
            val dx = (lon - t.lon) * 111.32 * cos(Math.toRadians(lat))
            val dy = (lat - t.lat) * 110.57
            val km = hypot(dx, dy)
            if (best == null || km < best.second) best = Triple(t, km, dx to dy)
        }
        val (town, km, d) = best ?: return null
        if (km > 60) return null
        val miles = maxOf(1.0, (km * 0.621371 * 2).roundToInt() / 2.0)
        val bearing = (Math.toDegrees(atan2(d.first, d.second)) + 360) % 360
        val dir = directions[((bearing / 45).roundToInt()) % 8]
        val m = if (miles % 1.0 == 0.0) miles.toInt().toString() else Fmt.one(miles)
        return "$m mile${if (miles == 1.0) "" else "s"} $dir of ${town.name}"
    }

    private val californiaCounties = mapOf(
        "007" to "Butte", "011" to "Colusa", "019" to "Fresno", "021" to "Glenn", "031" to "Kings", "039" to "Madera",
        "047" to "Merced", "067" to "Sacramento", "077" to "San Joaquin", "099" to "Stanislaus", "101" to "Sutter",
        "107" to "Tulare", "113" to "Yolo", "115" to "Yuba", "029" to "Kern",
    )

    fun countyFromFips(fips: String?): String? = fips?.takeLast(3)?.let { californiaCounties[it] }

    /** The crop the field is known for: most frequent non-fallow crop over the last 10 years on record. */
    fun mainCrop(history: Map<Int, String>): String = history.keys.sorted().takeLast(10)
        .map { cropName(history[it]) }
        .filter { it != "Left fallow" && it != "Not recorded" }
        .groupingBy { it }.eachCount()
        .maxByOrNull { it.value }?.key ?: "Crop"

    /** "Rice in 7 of the last 10 years; left fallow 2016, 2020 and 2022." */
    fun recordLine(history: Map<Int, String>): String {
        val years = history.keys.sorted().takeLast(10)
        if (years.isEmpty()) return "No crop record yet."
        val main = mainCrop(history).substringBefore(",")
        val n = years.count { cropName(history[it]).startsWith(main) }
        val fallow = years.filter { cropName(history[it]) == "Left fallow" }
        val fallowText = if (fallow.isEmpty()) "" else "; left fallow ${andList(fallow.map(Int::toString))}"
        return "$main in $n of the last ${years.size} years$fallowText."
    }

    fun andList(items: List<String>): String = when (items.size) {
        0 -> ""
        1 -> items[0]
        else -> items.dropLast(1).joinToString(", ") + " and " + items.last()
    }

    fun history(loc: LocationDto): Map<Int, String> =
        loc.cropHistory.mapNotNull { (y, c) -> y.toIntOrNull()?.let { it to c } }.toMap()

    fun identity(loc: LocationDto): FieldIdentity {
        val hist = history(loc)
        val main = mainCrop(hist)
        val latestYear = hist.keys.maxOrNull()
        val acres = loc.acres ?: loc.areaHa?.value?.let(Units::haToAcres)
        val county = loc.countyName ?: countyFromFips(loc.countyFips)
        val near = nearTown(loc.centroid.lat, loc.centroid.lon)
        val name = loc.farmerName?.takeIf { it.isNotBlank() }
            ?: near?.let { "${main.substringBefore(",")} field $it" }
            ?: loc.name.ifBlank { loc.id }
        return FieldIdentity(
            id = loc.id,
            name = name,
            county = county,
            acres = acres?.roundToInt(),
            latestCropYear = latestYear,
            latestCrop = latestYear?.let { cropName(hist[it]) },
            mainCrop = main,
            recordLine = recordLine(hist),
            stateFieldNo = loc.dwrUniqueId,
            lat = loc.centroid.lat,
            lon = loc.centroid.lon,
        )
    }
}
