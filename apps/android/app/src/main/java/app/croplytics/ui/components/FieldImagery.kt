package app.croplytics.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import app.croplytics.domain.Imagery
import app.croplytics.domain.Rings
import app.croplytics.ui.theme.DataColors
import coil3.compose.AsyncImage
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.geometry.LatLngBounds
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
import org.maplibre.android.style.layers.LineLayer
import org.maplibre.android.style.layers.Property
import org.maplibre.android.style.layers.PropertyFactory
import org.maplibre.android.style.sources.GeoJsonSource
import org.maplibre.geojson.Feature
import org.maplibre.geojson.Point
import org.maplibre.geojson.Polygon


/** Satellite picture of the field with its outline: yellow line over a dark casing so it reads on any imagery. */
@Composable
fun FieldThumbnail(rings: Rings, modifier: Modifier = Modifier, widthPx: Int = 240, heightPx: Int = 180) {
    val box = remember(rings) { Imagery.box(rings, widthPx.toDouble() / heightPx) }
    Box(modifier.clipToBounds().background(Color(0xFF39402F))) {
        if (box != null) {
            AsyncImage(
                model = Imagery.exportUrl(box, widthPx, heightPx),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize(),
            )
            Canvas(Modifier.fillMaxSize()) {
                rings.forEach { ring ->
                    val path = Path()
                    ring.forEachIndexed { i, (lon, lat) ->
                        val (fx, fy) = box.fraction(lon, lat)
                        if (i == 0) path.moveTo(fx * size.width, fy * size.height) else path.lineTo(fx * size.width, fy * size.height)
                    }
                    path.close()
                    drawPath(path, Color.Black.copy(alpha = 0.55f), style = Stroke(3.5.dp.toPx(), join = StrokeJoin.Round))
                    drawPath(path, DataColors.selection, style = Stroke(1.6.dp.toPx(), join = StrokeJoin.Round))
                }
            }
        }
    }
}

/**
 * MapLibre map on Esri World Imagery with the field outline. [interactive] = false makes a still
 * header map (no gestures) that sits inside a scrolling page.
 */
@Composable
fun FieldMap(rings: Rings, interactive: Boolean, modifier: Modifier = Modifier, paddingDp: Int = 48) {
    val context = LocalContext.current
    val density = LocalDensity.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val mapView = remember { MapView(context).apply { onCreate(null) } }

    DisposableEffect(lifecycle, mapView) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_START -> mapView.onStart()
                Lifecycle.Event.ON_RESUME -> mapView.onResume()
                Lifecycle.Event.ON_PAUSE -> mapView.onPause()
                Lifecycle.Event.ON_STOP -> mapView.onStop()
                else -> Unit
            }
        }
        lifecycle.addObserver(observer)
        onDispose {
            lifecycle.removeObserver(observer)
            mapView.onPause()
            mapView.onStop()
            mapView.onDestroy()
        }
    }

    LaunchedEffect(rings, interactive) {
        val padPx = with(density) { paddingDp.dp.roundToPx() }
        mapView.getMapAsync { map ->
            map.uiSettings.apply {
                setAllGesturesEnabled(interactive)
                isCompassEnabled = interactive
                isLogoEnabled = false
                isAttributionEnabled = true
            }
            map.setStyle(Style.Builder().fromJson(Imagery.SATELLITE_STYLE)) { style ->
                val points = rings.map { ring -> ring.map { (lon, lat) -> Point.fromLngLat(lon, lat) } }
                if (points.isEmpty()) return@setStyle
                style.addSource(GeoJsonSource("field", Feature.fromGeometry(Polygon.fromLngLats(points))))
                style.addLayer(
                    LineLayer("field-casing", "field").withProperties(
                        PropertyFactory.lineColor("#1b1b1b"), PropertyFactory.lineWidth(5f), PropertyFactory.lineOpacity(0.6f),
                        PropertyFactory.lineJoin(Property.LINE_JOIN_ROUND),
                    ),
                )
                style.addLayer(
                    LineLayer("field-line", "field").withProperties(
                        PropertyFactory.lineColor("#ffd166"), PropertyFactory.lineWidth(2.2f), PropertyFactory.lineJoin(Property.LINE_JOIN_ROUND),
                    ),
                )
                val bounds = LatLngBounds.Builder().apply { rings.flatten().forEach { (lon, lat) -> include(LatLng(lat, lon)) } }.build()
                map.moveCamera(CameraUpdateFactory.newLatLngBounds(bounds, padPx))
                if (interactive) map.setMinZoomPreference(8.0)
            }
        }
    }

    AndroidView(factory = { mapView }, modifier = modifier)
}
