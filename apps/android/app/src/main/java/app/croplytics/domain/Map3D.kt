package app.croplytics.domain

import kotlin.math.cos
import kotlin.math.roundToInt
import kotlin.math.sqrt

/**
 * The "under the field" 3D stack and the satellite footprints, ported from the web app's MapView.tsx. Pure geometry and
 * words: the map draws them. Heights are metres above ground and rise with zoom between [Z0] and [Z1].
 */
object Map3D {
    const val Z0 = 12.5
    const val Z1 = 14.2
    val HOME_LAT = 37.35
    val HOME_LON = -119.9
    const val HOME_ZOOM = 5.75

    data class Box(val w: Double, val s: Double, val e: Double, val n: Double)
    data class Extrusion(val ring: List<Pair<Double, Double>>, val base: Double, val height: Double, val color: String)
    /** A label pinned to the right-hand corner of one slab (projected with its altitude). */
    data class StackLabel(val key: String, val alt: Double, val pad: Double, val color: String, val tag: String, val title: String, val value: String, val note: String)
    data class Stack(val cells: List<Extrusion>, val smap: List<Extrusion>, val grace: List<Extrusion>, val posts: List<Extrusion>, val shadow: List<List<Pair<Double, Double>>>, val labels: List<StackLabel>)

    fun bbox(rings: Rings): Box? {
        val pts = rings.flatten(); if (pts.isEmpty()) return null
        return Box(pts.minOf { it.first }, pts.minOf { it.second }, pts.maxOf { it.first }, pts.maxOf { it.second })
    }
    fun mPerDegLat() = 111320.0
    fun mPerDegLon(lat: Double) = 111320.0 * cos(Math.toRadians(lat))
    fun rect(w: Double, s: Double, e: Double, n: Double) = listOf(w to s, e to s, e to n, w to n, w to s)
    fun padded(b: Box, lat: Double, padM: Double) = rect(b.w - padM / mPerDegLon(lat), b.s - padM / mPerDegLat(), b.e + padM / mPerDegLon(lat), b.n + padM / mPerDegLat())

    /** Per-cell spatial offset (-1..1): the cell's mean greenness against the field's, as the web's convertGrid. */
    fun offsets(grid: CellGrid): List<Double> {
        val means = grid.cells.map { c -> c.nd.filterNotNull().takeIf { it.isNotEmpty() }?.average() ?: 0.0 }
        val mu = means.average().takeIf { !it.isNaN() } ?: 0.0
        val sd = sqrt(means.sumOf { (it - mu) * (it - mu) } / means.size.coerceAtLeast(1)).takeIf { it > 0 } ?: 1.0
        return means.map { clamp((it - mu) / (2 * sd), -1.0, 1.0) }
    }

    private fun band(v: Double, hi: String, mid: String, lo: String) = if (v >= 67) hi else if (v > 33) mid else lo

    fun stack(
        rings: Rings, lat: Double, areaHa: Double, grid: CellGrid, offsets: List<Double>, cal: FieldCalendar, regional: RegionalSeries?,
        t: Int, layersOn: Map<String, Boolean>,
    ): Stack? {
        val b = bbox(rings) ?: return null
        val s = grid.cols * grid.cellM / 990.0 // keep proportions across field sizes
        val tt = Calendars.dataT(cal, t)
        val fs = fieldState(cal, tt)
        val smap = regional?.let { latestAt(it.soil, t)?.first }
        val grace = regional?.let { latestAt(it.groundwater, t)?.first }
        val labels = mutableListOf<StackLabel>()
        val cellBase = 430 * s
        var cells = emptyList<Extrusion>()
        if (layersOn["hls"] == true) {
            val layer = Grid3D.layerFor(grid, tt)
            var sum = 0.0; var n = 0
            cells = grid.cells.mapIndexed { i, c ->
                val st = Grid3D.cellState(c, layer, fs)
                if (st.cls != 'u') { sum += st.ndvi; n++ }
                Extrusion(c.ring.chunked(2) { it[0] to it[1] }, cellBase, cellBase + (8 + Grid3D.height(st) * 175) * s, Grid3D.color(st, offsets.getOrElse(i) { 0.0 }))
            }
            labels += StackLabel(
                "hls", cellBase + 60 * s, 0.0, "#7ee081", "Sentinel-2 satellite, 100 ft squares",
                "The crop: ${(Cls.LABEL[fs.cls] ?: "").lowercase()}",
                if (n == 0) "No clear view (cloud)" else "Greenness ${String.format(java.util.Locale.US, "%.2f", sum / n)} on a 0 to 1 scale",
                "${grid.cells.size} squares · ${Grid3D.layerLabel(layer?.let { grid.layers[it] })}",
            )
        }
        var smapSlab = emptyList<Extrusion>()
        if (layersOn["smap"] == true) {
            val base = 235 * s; val col = smap?.let { Ramps.ramp(Ramps.SMAP, it) } ?: "#737a86"
            smapSlab = listOf(Extrusion(padded(b, lat, 110 * s), base, base + (14 + (smap ?: 10.0) * 0.42) * s, col))
            labels += StackLabel(
                "smap", base + 20 * s, 110 * s, "#5ab0ff",
                if (regional?.soilSource == "grace_da") "NASA GRACE-FO with a land model, root zone" else "NASA SMAP satellite",
                "Soil moisture in the root zone",
                smap?.let { "${band(it, "Wetter than usual", "About normal", "Drier than usual")} (${Fmt.ordinal(it.roundToInt())} percentile)" } ?: "No reading",
                if (fs.cls == 'w') "Reading is unreliable over standing water" else "One reading covers about ${(81 / (areaHa / 100)).roundToInt()} fields this size",
            )
        }
        var graceSlab = emptyList<Extrusion>()
        if (layersOn["grace"] == true) {
            val base = 45 * s; val col = grace?.let { Ramps.ramp(Ramps.GRACE, it) } ?: "#5d636e"
            graceSlab = listOf(Extrusion(padded(b, lat, 230 * s), base, base + (14 + (grace ?: 4.0) * 0.42) * s, col))
            labels += StackLabel(
                "grace", base + 16 * s, 230 * s, "#ff7eb6", "NASA GRACE-FO satellites", "Groundwater in the basin",
                grace?.let { "${band(it, "More than usual", "About normal", "Less than usual")} (${Fmt.ordinal(it.roundToInt())} percentile)" } ?: "No reading: gap between satellite missions",
                "Basin-wide signal, not your own well",
            )
        }
        // corner posts tie the slabs together
        val pw = 5 * s
        val posts = if (labels.size > 1) listOf(b.w to b.s, b.e to b.s, b.e to b.n, b.w to b.n).map { (x, y) ->
            Extrusion(rect(x - pw / mPerDegLon(lat), y - pw / mPerDegLat(), x + pw / mPerDegLon(lat), y + pw / mPerDegLat()), 0.0, cellBase, "#e8eef7")
        } else emptyList()
        return Stack(cells, smapSlab, graceSlab, posts, listOf(padded(b, lat, 230 * s)), labels)
    }

    /** A footprint: a dashed square for basin-scale datasets or a line grid for field-scale ones, with its label box. */
    data class Footprint(val id: String, val color: String, val square: List<Pair<Double, Double>>?, val gridLines: List<List<Pair<Double, Double>>>, val labelAt: Pair<Double, Double>, val label: String)

    private val FP_OFFSET = mapOf("smap" to (0.37 to 0.6), "imerg" to (0.66 to 0.3), "grace" to (0.44 to 0.55))
    private val FP_WORD = mapOf("grace" to "Groundwater", "smap" to "Soil moisture", "imerg" to "Rainfall", "modis" to "Greenness")

    fun footprints(rings: Rings, lon: Double, lat: Double, layersOn: Map<String, Boolean>, smapLive: Boolean): List<Footprint> {
        val b = bbox(rings) ?: return emptyList()
        val mLon = mPerDegLon(lat); val mLat = mPerDegLat()
        return MapDatasets.ALL.filter { layersOn[it.id] == true && it.id != "hls" }.map { ds ->
            if (ds.regional) {
                val (ox, oy) = FP_OFFSET[ds.id] ?: (0.5 to 0.5)
                val w = lon - ds.footprintM * ox / mLon; val s = lat - ds.footprintM * oy / mLat
                val e = w + ds.footprintM / mLon; val n = s + ds.footprintM / mLat
                val miles = (ds.footprintM / 1609).roundToInt()
                Footprint(ds.id, ds.color, rect(w, s, e, n), emptyList(), e to n,
                    "${FP_WORD[ds.id] ?: ds.name}: this $miles-mile square${if (ds.id == "smap" && !smapLive) " (still downloading)" else ""}")
            } else {
                val pad = ds.footprintM * 2
                val w = b.w - pad / mLon; val e = b.e + pad / mLon; val s = b.s - pad / mLat; val n = b.n + pad / mLat
                val lines = mutableListOf<List<Pair<Double, Double>>>()
                var x = w; while (x <= e + 1e-9) { lines += listOf(x to s, x to n); x += ds.footprintM / mLon }
                var y = s; while (y <= n + 1e-9) { lines += listOf(w to y, e to y); y += ds.footprintM / mLat }
                Footprint(ds.id, ds.color, null, lines, e to s, "${ds.name} · ${ds.nativeScale} grid")
            }
        }
    }

    /** Pixel-size line for the layers sheet: "1 pixel ≈ 120 fields this size" or "≈ 650 pixels inside the field". */
    fun pixelRatio(ds: MapDataset, areaHa: Double): String {
        val fieldKm2 = areaHa / 100; val px = (ds.footprintM / 1000).let { it * it }
        return if (px >= fieldKm2) "1 pixel ≈ ${String.format(java.util.Locale.US, "%,d", (px / fieldKm2).roundToInt())} fields this size"
        else "≈ ${String.format(java.util.Locale.US, "%,d", (fieldKm2 / px).roundToInt())} pixels inside the field"
    }
}
