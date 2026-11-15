package app.croplytics.domain

import app.croplytics.ui.app.FieldItem
import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/** 3D stack inputs for Map3D.stack (mirrors the web app's nearest-preset borrow for pt_/my_ and while grid loads). */
data class Stack3dInputs(val grid: CellGrid, val calendar: FieldCalendar, val regional: RegionalSeries?)

object StackBorrow {
    fun isLite(id: String) = id.startsWith("pt_") || id.startsWith("my_")

  private fun haversineKm(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val r = 6371.0
        val p = Math.PI / 180
        val dLat = (lat2 - lat1) * p
        val dLon = (lon2 - lon1) * p
        val a = sin(dLat / 2) * sin(dLat / 2) + cos(lat1 * p) * cos(lat2 * p) * sin(dLon / 2) * sin(dLon / 2)
        return 2 * r * asin(sqrt(a))
    }

    /** Nearest prepared CA field (not BC, not lite): borrow grid / NASA series like api.ts nearestCaPreset. */
    fun nearest(target: FieldItem, fields: List<FieldItem>): FieldItem? {
        var best: FieldItem? = null
        var bestKm = Double.MAX_VALUE
        for (f in fields) {
            if (f.id.id == target.id.id || isLite(f.id.id) || f.id.region == "bc") continue
            val km = haversineKm(target.id.lat, target.id.lon, f.id.lat, f.id.lon)
            if (km < bestKm) {
                bestKm = km
                best = f
            }
        }
        return best
    }

    /** Move a preset grid onto another field's centroid (mockCells shift on the web). */
    fun shiftGrid(grid: CellGrid, from: FieldItem, to: FieldItem): CellGrid {
        val dLon = to.id.lon - from.id.lon
        val dLat = to.id.lat - from.id.lat
        return grid.copy(
            cells = grid.cells.map { c ->
                val ring = buildList(c.ring.size) { c.ring.chunked(2).forEach { (lon, lat) -> add(lon + dLon); add(lat + dLat) } }
                c.copy(ring = ring)
            },
        )
    }

    fun inputs(
        target: FieldItem,
        fields: List<FieldItem>,
        grid: CellGrid?,
        calendar: FieldCalendar?,
        regional: RegionalSeries?,
        borrow: FieldItem?,
        borrowGrid: CellGrid?,
        borrowCalendar: FieldCalendar?,
        borrowRegional: RegionalSeries?,
    ): Stack3dInputs? {
        val preset = borrow ?: nearest(target, fields)
        val cal = calendar ?: borrowCalendar ?: return null
        val reg = regional ?: borrowRegional
        val g = when {
            grid != null -> grid
            borrowGrid != null && preset != null -> shiftGrid(borrowGrid, preset, target)
            else -> return null
        }
        return Stack3dInputs(g, cal, reg)
    }
}