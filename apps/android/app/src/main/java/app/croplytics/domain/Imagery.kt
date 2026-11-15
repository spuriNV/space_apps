package app.croplytics.domain

import java.util.Locale
import kotlin.math.PI
import kotlin.math.ln
import kotlin.math.tan

/**
 * Satellite thumbnails from Esri World Imagery (the same imagery as the map, CONTRACT.md), cut to
 * a box around the field in Web Mercator so the outline overlay lines up pixel for pixel.
 */
object Imagery {
    const val TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    const val ATTRIBUTION = "Imagery: Esri, Maxar, Earthstar Geographics"
    private const val R = 6378137.0

    fun mercX(lon: Double) = lon * PI / 180 * R
    fun mercY(lat: Double) = ln(tan(PI / 4 + lat * PI / 180 / 2)) * R

    data class Box(val minX: Double, val minY: Double, val maxX: Double, val maxY: Double) {
        /** Field point to a 0..1 position inside the box (y from the top). */
        fun fraction(lon: Double, lat: Double) = ((mercX(lon) - minX) / (maxX - minX)).toFloat() to ((maxY - mercY(lat)) / (maxY - minY)).toFloat()
    }

    /** A box with the field filling about 60% of it, at the given width:height aspect. */
    fun box(rings: List<List<Pair<Double, Double>>>, aspect: Double, fill: Double = 0.6): Box? {
        val pts = rings.flatten()
        if (pts.isEmpty()) return null
        val xs = pts.map { mercX(it.first) }
        val ys = pts.map { mercY(it.second) }
        val cx = (xs.min() + xs.max()) / 2
        val cy = (ys.min() + ys.max()) / 2
        var w = (xs.max() - xs.min()) / fill
        var h = (ys.max() - ys.min()) / fill
        if (w / h < aspect) w = h * aspect else h = w / aspect
        w = maxOf(w, 600.0)
        h = maxOf(h, 600.0 / aspect)
        return Box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    }

    fun exportUrl(box: Box, widthPx: Int, heightPx: Int): String = String.format(
        Locale.US,
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?bbox=%.1f,%.1f,%.1f,%.1f&bboxSR=3857&imageSR=3857&size=%d,%d&format=jpg&f=image",
        box.minX, box.minY, box.maxX, box.maxY, widthPx, heightPx,
    )

    /** Raster style for MapLibre: Esri World Imagery only, no labels, no key. */
    val SATELLITE_STYLE = """
        {"version":8,"name":"CropLytics satellite",
         "sources":{"esri":{"type":"raster","tiles":["$TILE_URL"],"tileSize":256,"maxzoom":19,"attribution":"$ATTRIBUTION"}},
         "layers":[{"id":"background","type":"background","paint":{"background-color":"#1d221b"}},
                   {"id":"esri","type":"raster","source":"esri"}]}
    """.trimIndent()
}

typealias Rings = List<List<Pair<Double, Double>>>
