package app.croplytics.ui.map

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.MutableState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.croplytics.domain.Map3D
import app.croplytics.ui.theme.CropLyticsTheme
import org.maplibre.android.geometry.LatLng
import kotlin.math.roundToInt
import kotlin.math.sin

fun hexColor(hex: String): Color = Color(("ff" + hex.removePrefix("#")).toLong(16))

private val INK = Color(0xFF191C16)
private val PAPER = Color(0xFFF7F6F0)
private val MUTED = Color(0xFF5A5E54)

/**
 * Labels pinned to each slab of the 3D stack (the web's stack-labels): projected with the slab's altitude, de-overlapped
 * vertically, with a leader line from the slab corner. Shown once the stack has risen past half way.
 */
@Composable
fun StackLabels(handle: MapHandle, tick: MutableState<Int>, stack: Map3D.Stack?, rings: List<List<Pair<Double, Double>>>, lat: Double, topInsetPx: Int) {
    @Suppress("UNUSED_VARIABLE") val t = tick.value // recompose on every camera move
    val m = handle.map ?: return
    if (stack == null || stack.labels.isEmpty()) return
    val cam = m.cameraPosition
    val f = ((cam.zoom - Map3D.Z0) / (Map3D.Z1 - Map3D.Z0)).coerceIn(0.0, 1.0)
    if (f < 0.55) return
    val b = Map3D.bbox(rings) ?: return
    val proj = m.projection
    val density = LocalDensity.current
    // metres per density-independent pixel -> screen pixels per metre
    val pxPerM = density.density / proj.getMetersPerPixelAtLatitude(lat)
    val lift = sin(Math.toRadians(cam.tilt))
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val wPx = constraints.maxWidth.toFloat()
        val labelW = with(density) { 190.dp.toPx() }
        val anchors = stack.labels.map { s ->
            val px = s.pad / Map3D.mPerDegLon(lat); val py = s.pad / Map3D.mPerDegLat()
            val corners = listOf(b.e + px to b.s - py, b.e + px to b.n + py, b.w - px to b.n + py, b.w - px to b.s - py).map { (x, y) ->
                val p = proj.toScreenLocation(LatLng(y, x))
                p.x to (p.y - (s.alt * f * pxPerM * lift).toFloat())
            }
            s to corners.maxBy { it.first }
        }.sortedBy { it.second.second }
        val lx = minOf(anchors.maxOf { it.second.first } + with(density) { 24.dp.toPx() }, wPx - labelW - with(density) { 8.dp.toPx() })
        var lastY = -1e9f
        val gap = with(density) { 96.dp.toPx() }
        val placed = anchors.map { (s, a) ->
            val y = maxOf(a.second - with(density) { 30.dp.toPx() }, lastY + gap, topInsetPx.toFloat())
            lastY = y; Triple(s, a, y)
        }
        Canvas(Modifier.fillMaxSize()) {
            placed.forEach { (s, a, y) ->
                val c = hexColor(s.color)
                val p = Path().apply { moveTo(a.first, a.second); lineTo(lx - 12.dp.toPx(), y + 30.dp.toPx()); lineTo(lx, y + 30.dp.toPx()) }
                drawPath(p, c, style = Stroke(1.5.dp.toPx()))
                drawCircle(Color(0xFF0B1016), 5.5.dp.toPx(), Offset(a.first, a.second)); drawCircle(c, 4.dp.toPx(), Offset(a.first, a.second))
            }
        }
        placed.forEach { (s, _, y) ->
            Column(
                Modifier
                    .offset { IntOffset(lx.roundToInt(), y.roundToInt()) }
                    .width(190.dp)
                    .background(PAPER, RoundedCornerShape(2.dp))
                    .border(1.dp, INK, RoundedCornerShape(2.dp))
                    .padding(start = 0.dp)
                    .testTag("stack-label-${s.key}"),
            ) {
                Row(Modifier.height(IntrinsicSize.Min)) {
                    Box(Modifier.width(4.dp).fillMaxHeight().background(hexColor(s.color)))
                    Column(Modifier.padding(horizontal = 8.dp, vertical = 5.dp)) {
                        Text(s.tag, fontSize = 10.sp, lineHeight = 12.sp, color = MUTED)
                        Text(s.title, fontSize = 13.sp, lineHeight = 16.sp, color = INK, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleSmall)
                        Text(s.value, fontSize = 12.sp, lineHeight = 15.sp, color = INK)
                        Text(s.note, fontSize = 10.sp, lineHeight = 12.sp, color = MUTED, style = MaterialTheme.typography.labelSmall)
                    }
                }
            }
        }
    }
}

/** Footprint labels: solid paper boxes with an ink border and the dataset's colour on the left, never bare text over imagery. */
@Composable
fun FootprintLabels(handle: MapHandle, tick: MutableState<Int>, footprints: List<Map3D.Footprint>) {
    @Suppress("UNUSED_VARIABLE") val t = tick.value
    val m = handle.map ?: return
    if (footprints.isEmpty() || m.cameraPosition.zoom < 7.5) return
    val density = LocalDensity.current
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val maxW = constraints.maxWidth; val maxH = constraints.maxHeight
        footprints.forEach { fp ->
            val p = m.projection.toScreenLocation(LatLng(fp.labelAt.second, fp.labelAt.first))
            if (p.x < 0 || p.y < 0 || p.x > maxW || p.y > maxH) return@forEach
            val wPx = with(density) { 200.dp.toPx() }
            Row(
                Modifier
                    .offset { IntOffset((p.x - wPx - with(density) { 6.dp.toPx() }).roundToInt().coerceAtLeast(4), (p.y + with(density) { 6.dp.toPx() }).roundToInt()) }
                    .widthIn(max = 200.dp)
                    .height(IntrinsicSize.Min)
                    .background(PAPER)
                    .border(1.dp, INK),
            ) {
                Box(Modifier.width(4.dp).fillMaxHeight().background(hexColor(fp.color)))
                Text(fp.label, Modifier.padding(horizontal = 6.dp, vertical = 3.dp), fontSize = 11.sp, lineHeight = 13.sp, color = INK)
            }
        }
    }
}

/** "Under the field": the colour key for the 3D cells. */
@Composable
fun UnderFieldHud(modifier: Modifier = Modifier) {
    Surface(modifier.testTag("hud"), shape = RoundedCornerShape(3.dp), color = PAPER, border = androidx.compose.foundation.BorderStroke(1.dp, INK), shadowElevation = 2.dp) {
        Column(Modifier.padding(horizontal = 10.dp, vertical = 6.dp)) {
            Text("Under the field", fontSize = 13.sp, color = INK, style = MaterialTheme.typography.titleSmall)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                listOf('b' to "Bare", 'p' to "Thin", 'c' to "Crop", 'w' to "Flooded").forEach { (c, l) ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(10.dp).background(hexColor(app.croplytics.domain.Cls.COLOR.getValue(c))))
                        Spacer(Modifier.width(3.dp)); Text(l, fontSize = 11.sp, color = INK)
                    }
                }
            }
            Text("taller = greener", fontSize = 10.sp, color = MUTED)
        }
    }
}

/** Map controls (App.tsx .controls): whole state, reset north, 2D/3D, zoom in/out. */
@Composable
fun MapControls(bearing: Double, pitch: Double, onHome: () -> Unit, onNorth: () -> Unit, onTilt: () -> Unit, onZoom: (Double) -> Unit, modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp), horizontalAlignment = Alignment.End) {
        @Composable
        fun Btn(desc: String, onClick: () -> Unit, content: @Composable () -> Unit) = Surface(
            onClick = onClick, modifier = Modifier.size(44.dp).semantics { contentDescription = desc },
            shape = RoundedCornerShape(3.dp), color = c.paper, border = androidx.compose.foundation.BorderStroke(1.dp, c.line), shadowElevation = 2.dp,
        ) { Box(contentAlignment = Alignment.Center) { content() } }
        Btn("Whole of California", onHome) { Icon(Icons.Filled.Home, null, tint = c.text, modifier = Modifier.size(20.dp)) }
        Btn("Reset north", onNorth) { Icon(Icons.Filled.KeyboardArrowUp, null, tint = c.text, modifier = Modifier.rotate(-bearing.toFloat())) }
        Btn(if (pitch > 5) "Flat 2D view" else "Tilt to 3D", onTilt) { Text(if (pitch > 5) "2D" else "3D", style = MaterialTheme.typography.labelLarge, color = c.text) }
        Btn("Zoom in", { onZoom(1.0) }) { Icon(Icons.Filled.Add, null, tint = c.text) }
        Btn("Zoom out", { onZoom(-1.0) }) { Text("−", style = MaterialTheme.typography.titleLarge, color = c.text) }
    }
}
