package app.croplytics.domain

import app.croplytics.data.remote.dto.CalendarDto
import app.croplytics.data.remote.dto.CalendarYearDto
import app.croplytics.data.remote.dto.ModelsDto
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.time.LocalDate

// ---------------- the satellite calendar as 36 ten-day classes per year (api.ts convertCalendar) ----------------

@Serializable
data class CalYear(
    val year: Int,
    val cdl: String,
    /** 36 classes from the greenness rule: b p c w u. */
    val rule: String,
    /** 36 classes from the machine-learning calendar; all "u" when it is not served. */
    val ml: String,
    /** Greenness interpolated to each step (0 where unknown). */
    val ndvi: List<Double>,
    val greenup: Int?,
    val senescence: Int?,
)

@Serializable
data class FieldCalendar(val locationId: String, val years: List<CalYear>, val hls: Boolean, val hasMl: Boolean) {
    fun year(y: Int) = years.firstOrNull { it.year == y }
    /** Step t, or null past the calendar. */
    fun at(t: Int): CalYear? = years.getOrNull(Timeline.yearOf(t) - Timeline.FIRST_YEAR)
}

object Calendars {
    private fun doyOf(y: Int, step: Int) = LocalDate.of(y, step / 3 + 1, listOf(5, 15, 25)[step % 3]).dayOfYear

    fun classString(ry: CalendarYearDto?, year: Int): String {
        if (ry == null) return "u".repeat(36)
        return buildString {
            for (k in 0 until 36) {
                val q = doyOf(year, k)
                append(Cls.of(ry.segments.firstOrNull { q in it.startDoy..it.endDoy }?.cls))
            }
        }
    }

    private fun stepOfIso(iso: String?): Int? = iso?.let { Timeline.stepOf(Timeline.dateToT(it)) }

    fun convert(id: String, real: CalendarDto, ml: CalendarDto?, hist: Map<Int, String>, years: List<Int>, hls: Boolean): FieldCalendar {
        val out = years.map { year ->
            val ry = real.years.firstOrNull { it.year == year }
            val cdl = hist[year] ?: "Not published yet"
            if (ry == null) return@map CalYear(year, cdl, "u".repeat(36), "u".repeat(36), List(36) { 0.0 }, null, null)
            val obs = ry.observations.filter { it.ndvi != null }.map { LocalDate.parse(it.date.take(10)).toEpochDay() to it.ndvi!! }
            val ndvi = (0 until 36).map { k ->
                val tt = LocalDate.of(year, k / 3 + 1, listOf(5, 15, 25)[k % 3]).toEpochDay()
                val i = obs.indexOfFirst { it.first >= tt }
                val a = if (i > 0) obs[i - 1] else if (i == -1) obs.lastOrNull() else null
                val b = if (i >= 0) obs[i] else null
                when {
                    a != null && b != null && b.first - a.first <= 30 -> a.second + (b.second - a.second) * (tt - a.first) / (b.first - a.first).coerceAtLeast(1)
                    else -> (b ?: a)?.second ?: 0.0
                }
            }
            val up = ry.markers.firstOrNull { it.type == "green_up" && it.date.startsWith("$year") }
            val dn = ry.markers.firstOrNull { it.type == "senescence_harvest" && it.date.startsWith("$year") && (up == null || it.date > up.date) }
            CalYear(year, cdl, classString(ry, year), ml?.let { m -> classString(m.years.firstOrNull { it.year == year }, year) } ?: "u".repeat(36), ndvi, stepOfIso(up?.date), stepOfIso(dn?.date))
        }
        return FieldCalendar(id, out, hls, ml != null)
    }

    /** Last step with a clear satellite reading (the calendar ends where the processed imagery ends). */
    fun lastDataT(cal: FieldCalendar): Int {
        for (t in cal.years.size * 36 - 1 downTo 0) {
            val c = cal.years.getOrNull(t / 36)?.rule?.getOrNull(t % 36)
            if (c != null && c != 'u') return t
        }
        return 0
    }

    /** The date the satellite answers come from: t, or the latest reading if t is past it. */
    fun dataT(cal: FieldCalendar, t: Int) = minOf(t, lastDataT(cal))

    /** Latest clear step at or before t, at most [maxBack] steps back. */
    fun latestClearT(cal: FieldCalendar, t: Int, maxBack: Int = 4): Int? {
        var k = t
        while (k >= 0 && t - k <= maxBack) {
            val c = cal.at(k)?.rule?.getOrNull(Timeline.stepOf(k))
            if (c != null && c != 'u') return k
            k--
        }
        return null
    }
}

data class FieldState(val cls: Char, val ndvi: Double, val disagree: Boolean, val ruleCls: Char, val mlCls: Char)

fun fieldState(cal: FieldCalendar, t: Int): FieldState {
    val y = cal.at(t) ?: return FieldState('u', 0.0, false, 'u', 'u')
    val d = Timeline.stepOf(t)
    val r = y.rule[d]; val m = y.ml[d]
    return FieldState(r, y.ndvi[d], r != m && m != 'u', r, m)
}

// ---------------- NASA series per 10-day step (GET .../nasa_series) ----------------

@Serializable
data class RegionalSeries(
    /** Soil moisture percentile per step: SMAP root zone when cached, else GRACE-FO data assimilation root zone. */
    val soil: List<Double?>,
    val soilSource: String?,
    val groundwater: List<Double?>,
    /** OPERA water fraction per step (fallback for the standing-water record). */
    val dswx: List<Pair<String, Double>> = emptyList(),
) {
    val hasSoil get() = soilSource != null
    val hasGroundwater get() = groundwater.any { it != null }
}

/** Latest value at or before t, and its step (weekly products lag a few weeks). */
fun latestAt(vals: List<Double?>, t: Int, maxBack: Int = 12): Pair<Double, Int>? {
    var k = minOf(t, vals.size - 1)
    while (k >= 0 && t - k <= maxBack) { vals[k]?.let { return it to k }; k-- }
    return null
}

object Parsers {
    private fun JsonElement?.num(): Double? = (this as? JsonPrimitive)?.doubleOrNull
    private fun JsonElement?.str(): String? = (this as? JsonPrimitive)?.contentOrNull

    fun regional(body: JsonObject, years: List<Int>): RegionalSeries {
        val n = years.size * 36
        val rows = body["rows"]?.jsonArray.orEmpty().mapNotNull { it as? JsonObject }
        fun series(key: String): List<Double?>? {
            val out = MutableList<Double?>(n) { null }; var c = 0
            for (r in rows) {
                val d = r["date"].str() ?: continue; val v = r[key].num() ?: continue
                val t = Timeline.dateToT(d)
                if (t in 0 until n) { out[t] = v; c++ }
            }
            return out.takeIf { c > 0 }
        }
        val smap = series("smap_rootzone_pct"); val gda = series("grace_rootzone_pct"); val gw = series("grace_gw_pct")
        val dswx = rows.mapNotNull { r -> val v = r["dswx_water_frac"].num(); val d = r["date"].str(); if (v != null && d != null) d to v else null }
        return RegionalSeries(smap ?: gda ?: List(n) { null }, if (smap != null) "smap" else if (gda != null) "grace_da" else null, gw ?: List(n) { null }, dswx)
    }

    /** The 30 m grid (backend/field grid.geojson), kept compact: outer ring, share inside the field, greenness per layer. */
    fun grid(body: JsonObject): CellGrid {
        val layers = body["layers"]?.jsonArray.orEmpty().mapNotNull { e ->
            val o = e as? JsonObject ?: return@mapNotNull null
            GridLayer(o["key"].str() ?: return@mapNotNull null, o["kind"].str() ?: "quarter_median", (o["year"] as? JsonPrimitive)?.intOrNull,
                (o["quarter"] as? JsonPrimitive)?.intOrNull, (o["n_scenes"] as? JsonPrimitive)?.intOrNull, o["date"].str())
        }
        val keys = layers.map { it.key }
        var rows = 0; var cols = 0
        val cells = body["features"]?.jsonArray.orEmpty().mapNotNull { f ->
            val o = f as? JsonObject ?: return@mapNotNull null
            val g = o["geometry"]?.jsonObject ?: return@mapNotNull null
            if (g["type"].str() != "Polygon") return@mapNotNull null
            val p = o["properties"]?.jsonObject ?: return@mapNotNull null
            if ((p["area_m2"].num() ?: 0.0) < 150) return@mapNotNull null
            val ring = (g["coordinates"] as? JsonArray)?.firstOrNull()?.jsonArray.orEmpty().flatMap { pt -> (pt as JsonArray).take(2).map { it.jsonPrimitive.doubleOrNull ?: 0.0 } }
            val r = (p["row"] as? JsonPrimitive)?.intOrNull ?: 0; val c = (p["col"] as? JsonPrimitive)?.intOrNull ?: 0
            rows = maxOf(rows, r + 1); cols = maxOf(cols, c + 1)
            Cell(ring, p["frac_in_field"].num() ?: 1.0, keys.map { p[it].num() })
        }
        return CellGrid(30, rows, cols, layers, cells)
    }

    /** The daily record (GET .../daily), only the columns the answers use. */
    fun daily(body: JsonObject): Daily {
        val rows = body["rows"]?.jsonArray.orEmpty().mapNotNull { it as? JsonObject }
        return Daily(
            dates = rows.map { it["date"].str() ?: "" },
            stTmax = rows.map { it["ncei_tmax_c"].num() ?: it["eccc_tmax_c"].num() },
            stTmin = rows.map { it["ncei_tmin_c"].num() ?: it["eccc_tmin_c"].num() },
            stPrecip = rows.map { it["ncei_precip_mm"].num() ?: it["eccc_precip_mm"].num() },
            imerg = rows.map { it["imerg_precip_mm"].num() },
            eto = rows.map { it["eto_mm"].num() },
        )
    }

    /** How good the machine-learning calendar is (api.ts mlInfo): tested on 2022, a year it never trained on. */
    fun ml(models: ModelsDto?, detector: String?, disagreePct: Double?): MLInfo? {
        val method = detector ?: "random_forest"
        val m = models?.items?.firstOrNull { it.task == "bare_cover" && it.method == method && it.id.contains("_year_v1") && !it.id.contains("spatial") }
        fun metric(k: String) = (m?.metrics?.get(k) as? JsonPrimitive)?.doubleOrNull
        val acc = metric("accuracy_2022"); val f1 = metric("f1_bare_2022")
        return MLInfo(acc, f1, acc != null && f1 != null && acc >= 0.85 && f1 >= 0.8, acc != null && acc > 0.97, disagreePct, method.replace('_', ' '))
    }
}

@Serializable
data class MLInfo(val acc2022: Double?, val f1Bare2022: Double?, val meetsTarget: Boolean, val inflated: Boolean, val disagreePct: Double?, val model: String)

// ---------------- the 30 m grid for the 3D view ----------------

@Serializable
data class GridLayer(val key: String, val kind: String, val year: Int? = null, val quarter: Int? = null, val nScenes: Int? = null, val date: String? = null)

/** One 30 m cell: outer ring as flat lon,lat pairs, share inside the field, greenness per grid layer (aligned to [CellGrid.layers]). */
@Serializable
data class Cell(val ring: List<Double>, val frac: Double, val nd: List<Double?>)

@Serializable
data class CellGrid(val cellM: Int, val rows: Int, val cols: Int, val layers: List<GridLayer>, val cells: List<Cell>)

data class CellState(val cls: Char, val ndvi: Double)

object Grid3D {
    /** The grid layer for step t: a single clear scene within 12 days wins, else that quarter's median. */
    fun layerFor(grid: CellGrid, t: Int): Int? {
        val y = Timeline.yearOf(t); val d = Timeline.stepOf(t); val m = d / 3 + 1
        val tt = LocalDate.of(y, m, listOf(5, 15, 25)[d % 3]).toEpochDay()
        val scene = grid.layers.indexOfFirst { it.kind == "scene" && it.date != null && kotlin.math.abs(LocalDate.parse(it.date.take(10)).toEpochDay() - tt) <= 12 }
        if (scene >= 0) return scene
        return grid.layers.indexOfFirst { it.kind == "quarter_median" && it.year == y && it.quarter == (m - 1) / 3 + 1 }.takeIf { it >= 0 }
    }

    fun layerLabel(l: GridLayer?): String = when {
        l == null -> "no image for this date"
        l.kind == "scene" -> "image of ${Timeline.fmtDate(l.date)}"
        else -> "${listOf("Jan–Mar", "Apr–Jun", "Jul–Sep", "Oct–Dec")[(l.quarter ?: 1) - 1]} ${l.year}, middle of ${l.nScenes} image${if (l.nScenes == 1) "" else "s"}"
    }

    fun cellState(c: Cell, layer: Int?, fs: FieldState): CellState {
        val v = layer?.let { c.nd.getOrNull(it) } ?: return CellState('u', 0.0)
        val cls = if (fs.cls == 'w') 'w' else if (v < 0.2) 'b' else if (v <= 0.35) 'p' else 'c'
        return CellState(cls, v)
    }

    fun color(s: CellState, v: Double): String = when (s.cls) {
        'u' -> "#7b818c"
        'w' -> Ramps.ramp(listOf(-1.0 to "#2f86db", 1.0 to "#56aaf0"), v)
        'b' -> Ramps.ramp(listOf(-1.0 to "#8f5c30", 1.0 to "#bd8650"), v)
        'p' -> Ramps.ramp(listOf(0.2 to "#cfd98a", 0.35 to "#a9d46c"), s.ndvi)
        else -> Ramps.ramp(Ramps.NDVI, s.ndvi)
    }

    /** 0..1 extrusion height: taller = greener. */
    fun height(s: CellState): Double = when (s.cls) { 'u' -> 0.03; 'w' -> 0.02; else -> clamp(s.ndvi, 0.05, 1.0) }
}

// ---------------- daily weather (compact) ----------------

@Serializable
data class Daily(
    val dates: List<String>,
    val stTmax: List<Double?>,
    val stTmin: List<Double?>,
    val stPrecip: List<Double?>,
    val imerg: List<Double?>,
    val eto: List<Double?>,
)
