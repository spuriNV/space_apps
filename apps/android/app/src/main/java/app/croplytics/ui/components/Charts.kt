package app.croplytics.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.croplytics.domain.Cls
import app.croplytics.domain.Meter
import app.croplytics.domain.YearLogic
import app.croplytics.ui.map.hexColor
import app.croplytics.ui.theme.CropLyticsTheme

fun DrawScope.drawHatch(color: Color, step: Float, stroke: Float) {
    var x = -size.height
    while (x < size.width) { drawLine(color, Offset(x, size.height), Offset(x + size.height, 0f), stroke); x += step }
}

fun clsColor(c: Char): Color = hexColor(Cls.COLOR[c] ?: "#6b7280")

/**
 * One year as 36 ten-day cells (b p c w, hatched where there was no clear view), a tick at [todayStep], optional marks
 * (rain days, OPERA water, stress weeks) and tap-a-cell to move the viewing date.
 */
@Composable
fun CoverStrip(rule: String, todayStep: Int?, modifier: Modifier = Modifier, height: Float = 14f, marks: List<YearLogic.Mark> = emptyList(), onStep: ((Int) -> Unit)? = null) {
    val c = CropLyticsTheme.colors
    Canvas(
        modifier.fillMaxWidth().height(height.dp).then(
            if (onStep != null) Modifier.pointerInput(rule) { detectTapGestures { p -> onStep((p.x / size.width * 36).toInt().coerceIn(0, 35)) } } else Modifier,
        ),
    ) {
        val w = size.width / 36
        rule.forEachIndexed { i, ch ->
            val left = i * w
            if (ch == 'u') clipRect(left, 0f, left + w, size.height) { drawRect(c.track, Offset(left, 0f), Size(w, size.height)); drawHatch(c.muted.copy(alpha = 0.55f), 4.dp.toPx(), 1.dp.toPx()) }
            else drawRect(clsColor(ch), Offset(left, 0f), Size(w + 0.5f, size.height))
        }
        marks.forEach { m ->
            val x = (m.step + 0.5f) * w
            when {
                m.kind == "opera" -> drawRect(Color(0xFF1F6FB8), Offset(m.step * w, 0f), Size(w, 3.dp.toPx()))
                m.kind.startsWith("stress") -> drawCircle(if (m.kind.endsWith("both")) Color(0xFFA12A1C) else Color(0xFFE07A5F), 2.6.dp.toPx(), Offset(x, size.height - 3.dp.toPx()))
                else -> { // rain day: a dark tick, filled red when it fell on bare ground
                    drawLine(c.mark, Offset(x, -1f), Offset(x, size.height + 1f), 1.5.dp.toPx())
                    if (m.hit) drawCircle(Color(0xFFA12A1C), 2.4.dp.toPx(), Offset(x, size.height / 2))
                }
            }
        }
        if (todayStep != null) { val x = (todayStep + 0.5f) * w; drawLine(c.mark, Offset(x, -2.dp.toPx()), Offset(x, size.height + 2.dp.toPx()), 2.dp.toPx()) }
    }
}

@Composable
fun MonthTicks(modifier: Modifier = Modifier) {
    Row(modifier.fillMaxWidth()) { listOf("Jan", "Apr", "Jul", "Oct").forEach { Text(it, Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, color = CropLyticsTheme.colors.muted) } }
}

@Composable
fun MonthRow(modifier: Modifier = Modifier) {
    Row(modifier.fillMaxWidth()) { app.croplytics.domain.Timeline.MONTHS.forEach { Text(it.take(1), Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, color = CropLyticsTheme.colors.muted) } }
}

/** Colour key in words. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun CoverKey(items: List<Pair<Char, String>>, modifier: Modifier = Modifier, extra: @Composable () -> Unit = {}) {
    FlowRow(modifier, horizontalArrangement = Arrangement.spacedBy(10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        items.forEach { (cls, label) ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (cls == 'u') Hatch(Modifier.size(10.dp)) else Canvas(Modifier.size(10.dp)) { drawRect(clsColor(cls)) }
                Spacer(Modifier.width(4.dp)); Text(label, style = MaterialTheme.typography.labelSmall, color = CropLyticsTheme.colors.muted)
            }
        }
        extra()
    }
}

/** A reading with a bar and one reference line (normal, limit, full canopy). Spoken as one sentence. */
@Composable
fun MeterView(m: Meter, modifier: Modifier = Modifier, unavailable: Boolean = false) {
    val c = CropLyticsTheme.colors
    Column(modifier.then(if (m.value != null) Modifier.clearAndSetSemantics { contentDescription = m.spoken } else Modifier), verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(m.label, style = MaterialTheme.typography.labelSmall, color = c.muted)
        when {
            m.value != null -> {
                CountUpText(m.value, MaterialTheme.typography.titleMedium, if (m.warn) c.warn else c.text)
                // bars glide to their value (spec motion); the reference mark is a square-topped tick
                var shown by remember(m.value) { mutableStateOf(false) }
                LaunchedEffect(m.value) { shown = true }
                val fill by animateFloatAsState(if (shown) (m.fill ?: 0f) else 0f, motion(600), label = "fill")
                Canvas(Modifier.fillMaxWidth().height(12.dp).padding(vertical = 2.dp)) {
                    val r = CornerRadius(size.height / 2)
                    drawRoundRect(c.track, cornerRadius = r)
                    if (m.fill != null) drawRoundRect(if (m.warn) c.warn else c.accent, size = Size(size.width * fill.coerceIn(0f, 1f), size.height), cornerRadius = r)
                    m.mark?.let { k -> val x = size.width * k.coerceIn(0f, 1f); drawLine(c.mark, Offset(x, -3.dp.toPx()), Offset(x, size.height + 3.dp.toPx()), 2.dp.toPx()) }
                }
                if (m.note.isNotEmpty()) Text(m.note, style = MaterialTheme.typography.labelSmall, color = c.muted)
            }
            unavailable -> Text("Not available", style = MaterialTheme.typography.bodySmall, color = c.muted)
            else -> { Skeleton(height = 18.dp, widthFraction = 0.6f); Skeleton(height = 8.dp) }
        }
    }
}

/** Soil and groundwater on one 0-100 percentile track; 50 is normal. */
@Composable
fun PercentileTrack(soil: Int?, gw: Int?, note: String, ready: Boolean, modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    val soilCol = Color(0xFF8A5A2B); val gwCol = Color(0xFF1F6FB8)
    Column(modifier.clearAndSetSemantics { contentDescription = if (ready) "Soil moisture ${soil ?: "no reading"} percentile, groundwater ${gw ?: "no reading"} percentile; 50 is normal" else "Soil and groundwater loading" }, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text("Soil and groundwater", style = MaterialTheme.typography.labelSmall, color = c.muted)
        if (!ready) { Skeleton(height = 18.dp); return@Column }
        var shown by remember(soil, gw) { mutableStateOf(false) }
        LaunchedEffect(soil, gw) { shown = true }
        val sv by animateFloatAsState(if (shown) (soil ?: 50).toFloat() else 50f, motion(600), label = "soil")
        val gv by animateFloatAsState(if (shown) (gw ?: 50).toFloat() else 50f, motion(600), label = "gw")
        Box(Modifier.fillMaxWidth().height(20.dp)) {
            Canvas(Modifier.fillMaxWidth().height(20.dp)) {
                val y = size.height / 2
                drawRoundRect(c.track, Offset(0f, y - 4.dp.toPx()), Size(size.width, 8.dp.toPx()), CornerRadius(4.dp.toPx()))
                drawLine(c.muted, Offset(size.width / 2, y - 7.dp.toPx()), Offset(size.width / 2, y + 7.dp.toPx()), 1.5.dp.toPx())
                val r = 6.dp.toPx()
                if (soil != null) { drawCircle(soilCol, r, Offset(size.width * sv / 100f, y)); drawCircle(c.raised, r, Offset(size.width * sv / 100f, y), style = Stroke(1.5.dp.toPx())) }
                if (gw != null) { drawCircle(gwCol, r, Offset(size.width * gv / 100f, y)); drawCircle(c.raised, r, Offset(size.width * gv / 100f, y), style = Stroke(1.5.dp.toPx())) }
            }
        }
        Text(note, style = MaterialTheme.typography.labelSmall, color = c.muted)
    }
}

/** Sand / silt / clay as one stacked bar with a key underneath (shared.tsx SoilBar). */
@Composable
fun SoilBar(mix: Triple<Double, Double, Double>) {
    val c = CropLyticsTheme.colors
    val tot = (mix.first + mix.second + mix.third).takeIf { it > 0 } ?: 1.0
    val parts = listOf(Triple("Sand", mix.first, Color(0xFFD9B46A)), Triple("Silt", mix.second, Color(0xFFE9E3D3)), Triple("Clay", mix.third, Color(0xFF7A4A2B)))
    Column(Modifier.clearAndSetSemantics { contentDescription = parts.joinToString(", ") { "${it.first} ${it.second.toInt()}%" } }) {
        Canvas(Modifier.fillMaxWidth().height(12.dp)) {
            var x = 0f
            parts.forEach { (_, v, col) -> val w = (v / tot).toFloat() * size.width; drawRect(col, Offset(x, 0f), Size(w, size.height)); x += w }
            drawRect(c.line, style = Stroke(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            parts.forEach { (n, v, col) -> Row(verticalAlignment = Alignment.CenterVertically) { Canvas(Modifier.size(9.dp)) { drawRect(col) }; Text(" $n ${Math.round(v)}%", style = MaterialTheme.typography.labelSmall, color = c.text2) } }
        }
    }
}

/** Today vs an option on one track: bars show the likely range, ticks the best estimate (ComparePanel.tsx Bars). */
@Composable
fun RangeBars(today: app.croplytics.domain.Range, alt: app.croplytics.domain.Range, gain: Boolean, score: Boolean, modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    val max = if (score) 100.0 else (maxOf(today.high, alt.high) * 1.1).takeIf { it > 0 } ?: 1.0
    Column(modifier, verticalArrangement = Arrangement.spacedBy(2.dp)) {
        listOf(Triple("Today", today, c.muted), Triple("This", alt, if (gain) c.good else c.warn)).forEach { (label, r, col) ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(label, Modifier.width(40.dp), style = MaterialTheme.typography.labelSmall, color = c.muted)
                Canvas(Modifier.weight(1f).height(9.dp)) {
                    drawRect(c.track)
                    val x0 = (r.low / max).toFloat() * size.width; val x1 = (r.high / max).toFloat() * size.width
                    drawRect(col.copy(alpha = 0.8f), Offset(x0, 0f), Size((x1 - x0).coerceAtLeast(4.dp.toPx()), size.height))
                    val xv = (r.value / max).toFloat() * size.width
                    drawLine(c.mark, Offset(xv, -1f), Offset(xv, size.height + 1f), 2.dp.toPx())
                }
            }
        }
    }
}
