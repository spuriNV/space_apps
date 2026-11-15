package app.croplytics.ui.map

import android.graphics.PointF
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import app.croplytics.domain.BC
import app.croplytics.domain.Map3D
import app.croplytics.ui.app.CameraView
import app.croplytics.ui.app.FieldItem
import app.croplytics.ui.app.MapCommand
import kotlinx.coroutines.flow.Flow
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
import org.maplibre.android.style.expressions.Expression.eq
import org.maplibre.android.style.expressions.Expression.has
import org.maplibre.android.style.expressions.Expression.not
import org.maplibre.android.style.expressions.Expression.step
import org.maplibre.android.style.layers.CircleLayer
import org.maplibre.android.style.layers.PropertyFactory.circleColor
import org.maplibre.android.style.layers.PropertyFactory.circleOpacity
import org.maplibre.android.style.layers.PropertyFactory.circleRadius
import org.maplibre.android.style.layers.PropertyFactory.circleStrokeColor
import org.maplibre.android.style.layers.PropertyFactory.circleStrokeWidth
import org.maplibre.android.style.layers.PropertyFactory.textAllowOverlap
import org.maplibre.android.style.layers.PropertyFactory.textColor
import org.maplibre.android.style.layers.PropertyFactory.textField
import org.maplibre.android.style.layers.PropertyFactory.textFont
import org.maplibre.android.style.layers.PropertyFactory.textHaloColor
import org.maplibre.android.style.layers.PropertyFactory.textHaloWidth
import org.maplibre.android.style.layers.PropertyFactory.textSize
import org.maplibre.android.style.sources.GeoJsonOptions
import org.maplibre.android.style.expressions.Expression.get
import org.maplibre.android.style.expressions.Expression.interpolate
import org.maplibre.android.style.expressions.Expression.linear
import org.maplibre.android.style.expressions.Expression.literal
import org.maplibre.android.style.expressions.Expression.stop
import org.maplibre.android.style.expressions.Expression.switchCase
import org.maplibre.android.style.expressions.Expression.zoom
import org.maplibre.android.style.layers.FillExtrusionLayer
import org.maplibre.android.style.layers.FillLayer
import org.maplibre.android.style.layers.LineLayer
import org.maplibre.android.style.layers.Property
import org.maplibre.android.style.layers.PropertyFactory.fillColor
import org.maplibre.android.style.layers.PropertyFactory.fillExtrusionBase
import org.maplibre.android.style.layers.PropertyFactory.fillExtrusionColor
import org.maplibre.android.style.layers.PropertyFactory.fillExtrusionHeight
import org.maplibre.android.style.layers.PropertyFactory.fillExtrusionOpacity
import org.maplibre.android.style.layers.PropertyFactory.fillExtrusionVerticalGradient
import org.maplibre.android.style.layers.PropertyFactory.fillOpacity
import org.maplibre.android.style.layers.PropertyFactory.iconAllowOverlap
import org.maplibre.android.style.layers.PropertyFactory.iconAnchor
import org.maplibre.android.style.layers.PropertyFactory.iconImage
import org.maplibre.android.style.layers.PropertyFactory.iconIgnorePlacement
import org.maplibre.android.style.layers.PropertyFactory.lineColor
import org.maplibre.android.style.layers.PropertyFactory.lineDasharray
import org.maplibre.android.style.layers.PropertyFactory.lineOpacity
import org.maplibre.android.style.layers.PropertyFactory.lineWidth
import org.maplibre.android.style.layers.SymbolLayer
import org.maplibre.android.style.sources.GeoJsonSource
import org.maplibre.geojson.Feature
import org.maplibre.geojson.FeatureCollection
import org.maplibre.geojson.LineString
import org.maplibre.geojson.MultiLineString
import org.maplibre.geojson.Point
import org.maplibre.geojson.Polygon
import kotlin.math.abs

/** What the map shows; recomputed by the screen from the view model. */
data class MapContent(
    val fields: List<FieldItem>,
    val selectedId: String?,
    val stack: Map3D.Stack?,
    val footprints: List<Map3D.Footprint>,
    /** BC: reserve outlines near the field, context only (muted, dotted, never filled). */
    val reserves: List<app.croplytics.domain.Reserve> = emptyList(),
    /** Farm catalog pins (already filtered by crop). */
    val catalog: List<app.croplytics.domain.CatalogPin> = emptyList(),
    /** The polygon being drawn (lon, lat); null when not drawing. */
    val draw: List<Pair<Double, Double>>? = null,
)

/** Handle for the overlays (stack and footprint labels) to project points with altitude. */
class MapHandle { var map: MapLibreMap? = null }

private const val STYLE = """
{"version":8,"name":"CropLytics",
 "glyphs":"https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
 "sources":{
  "sat":{"type":"raster","tiles":["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],"tileSize":256,"maxzoom":18,"attribution":"Imagery © Esri, Maxar, Earthstar Geographics"},
  "omt":{"type":"vector","url":"https://tiles.openfreemap.org/planet","attribution":"© OpenMapTiles © OpenStreetMap"}},
 "layers":[
  {"id":"bg","type":"background","paint":{"background-color":"#0a0f15"}},
  {"id":"sat","type":"raster","source":"sat","paint":{"raster-saturation":-0.08,"raster-brightness-max":0.92}},
  {"id":"roads","type":"line","source":"omt","source-layer":"transportation","minzoom":8,"filter":["in",["get","class"],["literal",["motorway","trunk","primary"]]],"paint":{"line-color":"rgba(255,236,170,0.5)","line-width":["interpolate",["linear"],["zoom"],8,0.6,14,2.2]}},
  {"id":"admin","type":"line","source":"omt","source-layer":"boundary","filter":["all",["<=",["get","admin_level"],4],["!=",["get","maritime"],1]],"paint":{"line-color":"rgba(255,255,255,0.6)","line-width":1.1,"line-dasharray":[3,2]}},
  {"id":"place","type":"symbol","source":"omt","source-layer":"place","filter":["in",["get","class"],["literal",["city","town","state"]]],
   "layout":{"text-field":["coalesce",["get","name:en"],["get","name"]],"text-font":["Noto Sans Bold"],"text-size":["interpolate",["linear"],["zoom"],4,["match",["get","class"],"state",14,13],12,16],"text-transform":["match",["get","class"],"state","uppercase","none"],"text-padding":6},
   "paint":{"text-color":["match",["get","class"],"state","rgba(255,255,255,0.75)","#ffffff"],"text-halo-color":"rgba(5,10,16,0.85)","text-halo-width":1.5}}
 ]}
"""

private fun poly(ring: List<Pair<Double, Double>>) = Polygon.fromLngLats(listOf(ring.map { (x, y) -> Point.fromLngLat(x, y) }))
private fun fc(features: List<Feature>) = FeatureCollection.fromFeatures(features)
private fun ext(e: Map3D.Extrusion) = Feature.fromGeometry(poly(e.ring)).apply { addNumberProperty("b", e.base); addNumberProperty("h", e.height); addStringProperty("col", e.color) }

/**
 * The full interactive satellite map: pan, pinch-zoom, rotate and two-finger tilt; a pin for every field (tap to open it),
 * outlines, footprints, and the 3D stack that rises as you zoom in under the selected field.
 */
@Composable
fun CropMap(
    content: MapContent,
    commands: Flow<MapCommand>,
    bottomInsetPx: Int,
    topInsetPx: Int,
    handle: MapHandle,
    cameraTick: MutableState<Int>,
    onSelect: (String) -> Unit,
    onBC: () -> Unit,
    onCamera: (CameraView) -> Unit,
    modifier: Modifier = Modifier,
    onLongPress: (Double, Double) -> Unit = { _, _ -> },
    onCatalog: (app.croplytics.domain.CatalogPin) -> Unit = {},
    onDrawTap: (Double, Double) -> Unit = { _, _ -> },
) {
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val mapView = remember { MapView(context).apply { onCreate(null) } }
    var map by remember { mutableStateOf<MapLibreMap?>(null) }
    var style by remember { mutableStateOf<Style?>(null) }
    val latest by rememberUpdatedState(content)
    val select by rememberUpdatedState(onSelect)
    val bc by rememberUpdatedState(onBC)
    val report by rememberUpdatedState(onCamera)
    val longPress by rememberUpdatedState(onLongPress)
    val pickCatalog by rememberUpdatedState(onCatalog)
    val drawTap by rememberUpdatedState(onDrawTap)
    val insets = remember { intArrayOf(0, 0) }
    insets[0] = topInsetPx; insets[1] = bottomInsetPx

    DisposableEffect(lifecycle, mapView) {
        val observer = LifecycleEventObserver { _, e ->
            when (e) {
                Lifecycle.Event.ON_START -> mapView.onStart(); Lifecycle.Event.ON_RESUME -> mapView.onResume()
                Lifecycle.Event.ON_PAUSE -> mapView.onPause(); Lifecycle.Event.ON_STOP -> mapView.onStop()
                else -> Unit
            }
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer); mapView.onPause(); mapView.onStop(); mapView.onDestroy() }
    }

    LaunchedEffect(mapView) {
        mapView.getMapAsync { m ->
            map = m; handle.map = m
            m.uiSettings.apply { isCompassEnabled = false; isLogoEnabled = false; isAttributionEnabled = true; isRotateGesturesEnabled = true; isTiltGesturesEnabled = true }
            m.setMaxPitchPreference(70.0)
            m.cameraPosition = CameraPosition.Builder().target(LatLng(Map3D.HOME_LAT, Map3D.HOME_LON)).zoom(Map3D.HOME_ZOOM).build()
            var gesture = false
            m.addOnCameraMoveStartedListener { reason ->
                gesture = reason == MapLibreMap.OnCameraMoveStartedListener.REASON_API_GESTURE
            }
            fun tiltForDrill(c: CameraPosition) {
                val sel = latest.fields.firstOrNull { it.id.id == latest.selectedId } ?: return
                val t = c.target ?: return
                if (abs(t.latitude - sel.id.lat) > 0.06 || abs(t.longitude - sel.id.lon) > 0.08) return
                val f = ((c.zoom - (Map3D.Z0 - 0.3)) / (Map3D.Z1 - Map3D.Z0)).coerceIn(0.0, 1.0)
                val target = f * 58.0
                val bearing = if (f > 0) -22.0 * f else c.bearing
                if (abs(c.tilt - target) > 0.5 || (f > 0 && abs(c.bearing - bearing) > 0.5)) {
                    m.cameraPosition = CameraPosition.Builder(c).tilt(target).bearing(bearing).build()
                }
            }
            m.addOnCameraMoveListener {
                cameraTick.value++
                if (gesture) tiltForDrill(m.cameraPosition)
            }
            m.addOnCameraIdleListener {
                val c = m.cameraPosition
                report(CameraView(c.zoom, c.tilt, c.bearing, c.target?.latitude ?: 0.0, c.target?.longitude ?: 0.0))
                cameraTick.value++
                gesture = false
            }
            m.addOnMapLongClickListener { ll ->
                if (latest.draw == null) { mapView.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS); longPress(ll.latitude, ll.longitude) }
                true
            }
            m.addOnMapClickListener { ll ->
                if (latest.draw != null) { drawTap(ll.latitude, ll.longitude); return@addOnMapClickListener true }
                val pt: PointF = m.projection.toScreenLocation(ll)
                val hit = m.queryRenderedFeatures(pt, "pins-near", "pins-far", "field-hit")
                    .firstNotNullOfOrNull { f -> f.getStringProperty("id") }
                val cat = if (hit == null) m.queryRenderedFeatures(pt, "cat-pt", "cat-cluster").firstOrNull() else null
                when {
                    hit == "bc" -> { bc(); true }
                    hit != null -> { select(hit); true }
                    cat != null && cat.hasProperty("point_count") -> {
                        m.animateCamera(CameraUpdateFactory.newLatLngZoom(ll, m.cameraPosition.zoom + 2.0), 450); true
                    }
                    cat != null -> { latest.catalog.firstOrNull { it.id == cat.getStringProperty("id") }?.let(pickCatalog); true }
                    else -> false
                }
            }
            m.setStyle(Style.Builder().fromJson(STYLE)) { s ->
                s.addSource(GeoJsonSource("catalog", GeoJsonOptions().withCluster(true).withClusterRadius(40).withClusterMaxZoom(10)))
                listOf("draw", "reserves", "fp", "fpgrid", "field", "shadow", "posts", "slab-grace", "slab-smap", "cells", "pins").forEach { s.addSource(GeoJsonSource(it)) }
                s.addLayer(LineLayer("res-casing", "reserves").withProperties(lineColor("rgba(10,12,8,0.5)"), lineWidth(3.6f)))
                s.addLayer(LineLayer("res-line", "reserves").withProperties(lineColor("#f1ecdd"), lineOpacity(0.95f), lineWidth(2f), lineDasharray(arrayOf(3f, 2f))))
                s.addLayer(FillLayer("fp-fill", "fp").withProperties(fillColor(get("color")), fillOpacity(interpolate(linear(), zoom(), stop(8, 0.1f), stop(13, 0.03f)))))
                s.addLayer(LineLayer("fp-line", "fp").withProperties(lineColor(get("color")), lineWidth(2f), lineDasharray(arrayOf(2f, 1.5f))))
                s.addLayer(LineLayer("fpgrid-line", "fpgrid").withProperties(lineColor(get("color")), lineWidth(1f), lineOpacity(0.75f)).apply { minZoom = 11.5f })
                s.addLayer(FillLayer("shadow", "shadow").withProperties(fillColor("#000000"), fillOpacity(interpolate(linear(), zoom(), stop(Map3D.Z0, 0f), stop(Map3D.Z1, 0.42f)))).apply { minZoom = Map3D.Z0.toFloat() })
                s.addLayer(LineLayer("field-casing", "field").withProperties(lineColor("rgba(0,0,0,0.65)"), lineWidth(5f)))
                s.addLayer(LineLayer("field-line", "field").withProperties(lineColor(switchCase(eq(get("selected"), literal(true)), literal("#ffd166"), literal("rgba(255,255,255,0.75)"))), lineWidth(2f)))
                s.addLayer(FillLayer("field-hit", "field").withProperties(fillColor("#ffffff"), fillOpacity(interpolate(linear(), zoom(), stop(9, 0.25f), stop(11.5, 0.02f)))))
                fun extrusion(id: String, opacity: Float, minZ: Double) = s.addLayer(
                    FillExtrusionLayer(id, id).withProperties(
                        fillExtrusionColor(get("col")),
                        fillExtrusionBase(interpolate(linear(), zoom(), stop(Map3D.Z0, 0), stop(Map3D.Z1, get("b")))),
                        fillExtrusionHeight(interpolate(linear(), zoom(), stop(Map3D.Z0, 0), stop(Map3D.Z1, get("h")))),
                        fillExtrusionOpacity(opacity), fillExtrusionVerticalGradient(true),
                    ).apply { minZoom = minZ.toFloat() },
                )
                extrusion("posts", 0.55f, Map3D.Z0 + 0.4); extrusion("slab-grace", 0.86f, Map3D.Z0 + 0.1); extrusion("slab-smap", 0.84f, Map3D.Z0 + 0.1); extrusion("cells", 0.97f, 11.2)
                s.addLayer(CircleLayer("cat-cluster", "catalog").withFilter(has("point_count")).withProperties(
                    circleColor("#f7f6f0"), circleOpacity(0.92f), circleStrokeColor("#191c16"), circleStrokeWidth(1f),
                    circleRadius(step(get("point_count"), literal(13), stop(10, 16), stop(30, 20)))))
                s.addLayer(SymbolLayer("cat-count", "catalog").withFilter(has("point_count")).withProperties(
                    textField(get("point_count_abbreviated")), textFont(arrayOf("Noto Sans Bold")), textSize(13f), textAllowOverlap(true), textColor("#191c16")))
                s.addLayer(CircleLayer("cat-pt", "catalog").withFilter(not(has("point_count"))).withProperties(
                    circleColor(get("color")), circleRadius(interpolate(linear(), zoom(), stop(5, 5f), stop(12, 8f))), circleStrokeColor("#f7f6f0"), circleStrokeWidth(1.75f), circleOpacity(0.95f)))
                s.addLayer(SymbolLayer("cat-letter", "catalog").withFilter(not(has("point_count"))).withProperties(
                    textField(get("letter")), textFont(arrayOf("Noto Sans Bold")), textSize(11f), textAllowOverlap(true), textColor("#191c16"), textHaloColor("#f7f6f0"), textHaloWidth(1.5f)).apply { minZoom = 9f })
                s.addLayer(SymbolLayer("pins-far", "pins").withProperties(iconImage(get("far")), iconAnchor(Property.ICON_ANCHOR_BOTTOM), iconAllowOverlap(true), iconIgnorePlacement(true)).apply { maxZoom = 8.2f })
                s.addLayer(SymbolLayer("pins-near", "pins").withProperties(iconImage(get("near")), iconAnchor(Property.ICON_ANCHOR_BOTTOM), iconAllowOverlap(true), iconIgnorePlacement(true)).apply { minZoom = 8.2f })
                s.addLayer(FillLayer("draw-fill", "draw").withProperties(fillColor("#ffd166"), fillOpacity(0.25f)))
                s.addLayer(LineLayer("draw-line", "draw").withProperties(lineColor("#ffd166"), lineWidth(3f)))
                s.addLayer(CircleLayer("draw-pt", "draw").withProperties(circleColor("#ffffff"), circleRadius(6f), circleStrokeColor("#ffd166"), circleStrokeWidth(3f)))
                style = s
            }
        }
    }

    // ---------- fields, pins, footprints, stack ----------
    LaunchedEffect(style, content) {
        val s = style ?: return@LaunchedEffect
        fun src(id: String) = s.getSourceAs<GeoJsonSource>(id)
        src("field")?.setGeoJson(fc(content.fields.flatMap { f -> f.rings.map { r -> Feature.fromGeometry(poly(r)).apply { addStringProperty("id", f.id.id); addBooleanProperty("selected", f.id.id == content.selectedId) } } }))
        val pins = content.fields.map { f ->
            val on = f.id.id == content.selectedId
            val far = "far-${f.id.id}-$on"; val near = "near-${f.id.id}-$on"
            if (s.getImage(far) == null) s.addImage(far, PinIcons.pin(context, on))
            if (s.getImage(near) == null) s.addImage(near, PinIcons.pin(context, on, title = f.id.name, sub = "${f.id.acres ?: "?"} acres · ${f.id.latestCrop ?: "crop"} in ${f.id.latestCropYear ?: ""}"))
            Feature.fromGeometry(Point.fromLngLat(f.id.lon, f.id.lat)).apply { addStringProperty("id", f.id.id); addStringProperty("far", far); addStringProperty("near", near) }
        } + (if (content.fields.any { it.loc.isBC }) emptyList() else BC.PLACES).mapIndexed { i, p ->
            val far = "bc-far"; val near = "bc-near-$i"
            if (s.getImage(far) == null) s.addImage(far, PinIcons.pin(context, false, bc = true))
            if (s.getImage(near) == null) s.addImage(near, PinIcons.pin(context, false, bc = true, title = p.name, sub = "British Columbia · not set up yet"))
            Feature.fromGeometry(Point.fromLngLat(p.lon, p.lat)).apply { addStringProperty("id", "bc"); addStringProperty("far", far); addStringProperty("near", near) }
        }
        src("pins")?.setGeoJson(fc(pins))
        src("fp")?.setGeoJson(fc(content.footprints.mapNotNull { fp -> fp.square?.let { Feature.fromGeometry(poly(it)).apply { addStringProperty("color", fp.color) } } }))
        src("fpgrid")?.setGeoJson(fc(content.footprints.filter { it.gridLines.isNotEmpty() }.map { fp ->
            Feature.fromGeometry(MultiLineString.fromLineStrings(fp.gridLines.map { l -> LineString.fromLngLats(l.map { (x, y) -> Point.fromLngLat(x, y) }) })).apply { addStringProperty("color", fp.color) }
        }))
        src("reserves")?.setGeoJson(fc(content.reserves.flatMap { r -> r.rings.map { Feature.fromGeometry(LineString.fromLngLats(it.map { (x, y) -> Point.fromLngLat(x, y) })) } }))
        val st = content.stack
        src("cells")?.setGeoJson(fc(st?.cells?.map(::ext).orEmpty()))
        src("slab-smap")?.setGeoJson(fc(st?.smap?.map(::ext).orEmpty()))
        src("slab-grace")?.setGeoJson(fc(st?.grace?.map(::ext).orEmpty()))
        src("posts")?.setGeoJson(fc(st?.posts?.map(::ext).orEmpty()))
        src("shadow")?.setGeoJson(fc(st?.shadow?.map { Feature.fromGeometry(poly(it)) }.orEmpty()))
    }

    // ---------- farm catalog pins and the polygon being drawn ----------
    LaunchedEffect(style, content.catalog) {
        val s = style ?: return@LaunchedEffect
        s.getSourceAs<GeoJsonSource>("catalog")?.setGeoJson(fc(content.catalog.map { p ->
            Feature.fromGeometry(Point.fromLngLat(p.lon, p.lat)).apply {
                addStringProperty("id", p.id); addStringProperty("color", app.croplytics.domain.CatalogLogic.color(p.group)); addStringProperty("letter", app.croplytics.domain.CatalogLogic.letter(p.group))
            }
        }))
    }
    LaunchedEffect(style, content.draw) {
        val s = style ?: return@LaunchedEffect
        val d = content.draw.orEmpty()
        val feats = buildList {
            d.forEach { (x, y) -> add(Feature.fromGeometry(Point.fromLngLat(x, y))) }
            if (d.size >= 2) add(Feature.fromGeometry(LineString.fromLngLats((d + if (d.size >= 3) listOf(d.first()) else emptyList()).map { (x, y) -> Point.fromLngLat(x, y) })))
            if (d.size >= 3) add(Feature.fromGeometry(poly(d + d.first())))
        }
        s.getSourceAs<GeoJsonSource>("draw")?.setGeoJson(fc(feats))
    }

    // ---------- camera commands (MapView.tsx flyToField / flyHome / zoomBy / resetNorth / toggle3D) ----------
    LaunchedEffect(map) {
        val m = map ?: return@LaunchedEffect
        commands.collect { cmd ->
            fun pos(lat: Double, lon: Double, zoom: Double, tilt: Double, bearing: Double) =
                CameraPosition.Builder().target(LatLng(lat, lon)).zoom(zoom).tilt(tilt).bearing(bearing).padding(0.0, insets[0].toDouble(), 0.0, insets[1].toDouble()).build()
            when (cmd) {
                is MapCommand.FlyToField -> {
                    if (cmd.lat == 0.0 && cmd.lon == 0.0) return@collect
                    val small = cmd.small
                    val p = when (cmd.mode) {
                        MapCommand.FlyToField.Mode.Card -> pos(cmd.lat, cmd.lon, 10.6, 0.0, 0.0)
                        else -> pos(cmd.lat - if (small) 0.0006 else 0.001, cmd.lon, (if (small) 15.15 else 14.5) - if (cmd.mode == MapCommand.FlyToField.Mode.Year) 0.75 else 0.0,
                            if (cmd.mode == MapCommand.FlyToField.Mode.Year) 52.0 else 60.0, -24.0)
                    }
                    m.animateCamera(CameraUpdateFactory.newCameraPosition(p), 1800)
                }
                MapCommand.FlyHome -> m.animateCamera(CameraUpdateFactory.newCameraPosition(pos(Map3D.HOME_LAT, Map3D.HOME_LON, Map3D.HOME_ZOOM, 0.0, 0.0)), 1500)
                is MapCommand.FlyTo -> m.animateCamera(CameraUpdateFactory.newCameraPosition(pos(cmd.lat, cmd.lon, cmd.zoom, 0.0, 0.0)), 1500)
                is MapCommand.ZoomBy -> m.animateCamera(CameraUpdateFactory.zoomBy(cmd.delta), 250)
                MapCommand.ResetNorth -> m.animateCamera(CameraUpdateFactory.bearingTo(0.0), 300)
                MapCommand.Toggle3D -> m.animateCamera(CameraUpdateFactory.tiltTo(if (m.cameraPosition.tilt > 5) 0.0 else 58.0), 400)
            }
        }
    }

    AndroidView(factory = { mapView }, modifier = modifier)
}
