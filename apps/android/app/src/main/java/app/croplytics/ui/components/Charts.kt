package app.croplytics.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.croplytics.domain.BarReading
import app.croplytics.domain.Cover
import app.croplytics.domain.PercentileReading
import app.croplytics.ui.theme.CropLyticsTheme
import app.croplytics.ui.theme.DataColors

fun DrawScope.drawHatch(color: Color, step: Float, stroke: Float) {
    var x = -size.height
    while (x < size.width) {
        drawLine(color, Offset(x, size.height), Offset(x + size.height, 0f), stroke)
        x += step
    }
}

fun coverColor(c: Cover): Color = when (c) {
    Cover.Bare -> DataColors.bare
    Cover.Partial -> DataColors.partial
    Cover.Covered -> DataColors.covered
    Cover.Water -> DataColors.water
    Cover.Unknown -> DataColors.unknown
}

/**
 * One year as 36 ten-day cells: bare, thin, green, under water, or hatched where there was no
 * clear view. A tick marks today.
 */
@Composable
fun SeasonStripBar(steps: List<Cover>, todayStep: Int?, modifier: Modifier = Modifier, height: Float = 14f) {
    val c = CropLyticsTheme.colors
    Canvas(modifier.fillMaxWidth().height(height.dp)) {
        val w = size.width / steps.size.coerceAtLeast(1)
        steps.forEachIndexed { i, cover ->
            val left = i * w
            if (cover == Cover.Unknown) {
                clipRect(left, 0f, left + w, size.height) {
                    drawRect(c.track, Offset(left, 0f), Size(w, size.height))
                    drawHatch(c.muted.copy(alpha = 0.6f), 4.dp.toPx(), 1.dp.toPx())
                }
            } else {
                drawRect(coverColor(cover), Offset(left, 0f), Size(w + 0.5f, size.height))
            }
        }
        if (todayStep != null) {
            val x = (todayStep + 0.5f) * w
            drawLine(c.mark, Offset(x, -2.dp.toPx()), Offset(x, size.height + 2.dp.toPx()), 2.dp.toPx())
        }
    }
}

@Composable
fun MonthTicks(modifier: Modifier = Modifier) {
    Row(modifier.fillMaxWidth()) {
        listOf("Jan", "Apr", "Jul", "Oct").forEach {
            Text(it, Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, color = CropLyticsTheme.colors.muted)
        }
    }
}

/** Colour key for the strip, in words. */
@Composable
fun CoverKey(modifier: Modifier = Modifier) {
    val items = listOf(Cover.Covered to "green", Cover.Partial to "thin", Cover.Bare to "bare", Cover.Water to "water", Cover.Unknown to "no clear view")
    androidx.compose.foundation.layout.FlowRow(modifier, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        items.forEach { (cover, label) ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (cover == Cover.Unknown) Hatch(Modifier.size(10.dp)) else Canvas(Modifier.size(10.dp)) { drawRect(coverColor(cover)) }
                Spacer(Modifier.width(4.dp))
                Text(label, style = MaterialTheme.typography.labelSmall, color = CropLyticsTheme.colors.muted)
            }
        }
    }
}

/** A reading with a bar and one reference line (normal, limit, full canopy). Spoken as one sentence. */
@Composable
fun Meter(reading: BarReading?, label: String, modifier: Modifier = Modifier, unavailable: Boolean = false) {
    val c = CropLyticsTheme.colors
    Column(
        modifier.then(if (reading != null) Modifier.clearAndSetSemantics { contentDescription = reading.spoken } else Modifier),
        verticalArrangement = Arrangement.spacedBy(3.dp),
    ) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = c.muted)
        when {
            reading != null -> {
                Text(reading.value, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold), color = if (reading.warn) c.warn else c.text)
                Canvas(Modifier.fillMaxWidth().height(10.dp).padding(vertical = 1.dp)) {
                    drawRoundRect(c.track, cornerRadius = CornerRadius(1.dp.toPx()))
                    drawRect(if (reading.warn) c.warn else c.accent, size = Size(size.width * reading.fill.coerceIn(0f, 1f), size.height))
                    reading.mark?.let { m ->
                        val x = size.width * m.coerceIn(0f, 1f)
                        drawLine(c.mark, Offset(x, -3.dp.toPx()), Offset(x, size.height + 3.dp.toPx()), 2.dp.toPx())
                    }
                }
                Text(
                    reading.note + (reading.markLabel?.let { " · line = $it" } ?: ""),
                    style = MaterialTheme.typography.labelSmall,
                    color = c.muted,
                )
            }
            unavailable -> Text("Not available", style = MaterialTheme.typography.bodySmall, color = c.muted)
            else -> {
                Skeleton(height = 18.dp, widthFraction = 0.6f)
                Skeleton(height = 8.dp)
            }
        }
    }
}

/** Soil and groundwater on one 0-100 percentile track; 50 is normal. */
@Composable
fun PercentileTrack(reading: PercentileReading?, modifier: Modifier = Modifier, unavailable: Boolean = false) {
    val c = CropLyticsTheme.colors
    Column(
        modifier.then(if (reading != null) Modifier.clearAndSetSemantics { contentDescription = reading.spoken } else Modifier),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text("Soil and groundwater", style = MaterialTheme.typography.labelSmall, color = c.muted)
        when {
            reading != null -> {
                Box(Modifier.fillMaxWidth().height(22.dp)) {
                    Canvas(Modifier.fillMaxWidth().height(22.dp)) {
                        val y = size.height / 2
                        drawRoundRect(c.track, Offset(0f, y - 4.dp.toPx()), Size(size.width, 8.dp.toPx()), CornerRadius(1.dp.toPx()))
                        drawLine(c.muted, Offset(size.width / 2, y - 7.dp.toPx()), Offset(size.width / 2, y + 7.dp.toPx()), 1.5.dp.toPx())
                        val r = 6.dp.toPx()
                        reading.soil?.let { drawCircle(DataColors.soil, r, Offset(size.width * it / 100f, y)); drawCircle(c.paper, r, Offset(size.width * it / 100f, y), style = androidx.compose.ui.graphics.drawscope.Stroke(1.5.dp.toPx())) }
                        reading.groundwater?.let { drawCircle(DataColors.groundwater, r, Offset(size.width * it / 100f, y)); drawCircle(c.paper, r, Offset(size.width * it / 100f, y), style = androidx.compose.ui.graphics.drawscope.Stroke(1.5.dp.toPx())) }
                    }
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Dot(DataColors.soil); Text(" soil ", style = MaterialTheme.typography.labelSmall, color = c.muted)
                    Dot(DataColors.groundwater); Text(" groundwater", style = MaterialTheme.typography.labelSmall, color = c.muted)
                }
                Text(reading.note, style = MaterialTheme.typography.labelSmall, color = c.muted)
            }
            unavailable -> Text("Not available", style = MaterialTheme.typography.bodySmall, color = c.muted)
            else -> {
                Skeleton(height = 18.dp)
                Skeleton(height = 8.dp, widthFraction = 0.7f)
            }
        }
    }
}

@Composable
private fun Dot(color: Color) = Canvas(Modifier.size(9.dp)) { drawCircle(color) }

/** Today vs an option on one track: bars show the likely range, ticks the best estimate. */
@Composable
fun RangePair(todayLow: Double, todayHigh: Double, todayValue: Double, low: Double, high: Double, value: Double, better: Boolean, modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    val max = maxOf(todayHigh, high) * 1.1
    Column(modifier, verticalArrangement = Arrangement.spacedBy(2.dp)) {
        listOf(Triple("Today", Triple(todayLow, todayHigh, todayValue), c.muted), Triple("This", Triple(low, high, value), if (better) c.good else c.warn)).forEach { (label, r, color) ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(label, Modifier.width(44.dp), style = MaterialTheme.typography.labelSmall, color = c.muted)
                Canvas(Modifier.weight(1f).height(10.dp)) {
                    drawRect(c.track)
                    val x0 = (r.first / max).toFloat() * size.width
                    val x1 = (r.second / max).toFloat() * size.width
                    drawRect(color.copy(alpha = 0.75f), Offset(x0, 0f), Size((x1 - x0).coerceAtLeast(3.dp.toPx()), size.height))
                    val xv = (r.third / max).toFloat() * size.width
                    drawLine(c.mark, Offset(xv, -1f), Offset(xv, size.height + 1f), 2.dp.toPx())
                }
            }
        }
    }
}
