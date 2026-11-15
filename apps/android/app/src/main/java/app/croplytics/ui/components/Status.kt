package app.croplytics.ui.components

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.drawscope.clipRect
import app.croplytics.data.repository.LoadError
import app.croplytics.ui.theme.CropLyticsTheme
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Grey block that pulses gently while a value loads. */
@Composable
fun Skeleton(modifier: Modifier = Modifier, height: Dp = 14.dp, widthFraction: Float = 1f) {
    val t = rememberInfiniteTransition(label = "skeleton")
    val a by t.animateFloat(0.45f, 0.9f, infiniteRepeatable(tween(900), RepeatMode.Reverse), label = "alpha")
    Box(
        modifier
            .fillMaxWidth(widthFraction)
            .height(height)
            .alpha(a)
            .background(CropLyticsTheme.colors.track, RoundedCornerShape(6.dp)),
    )
}

/** A page-shaped skeleton: heading, a summary box and a few answer lines. */
@Composable
fun PageSkeleton(modifier: Modifier = Modifier) {
    Column(
        modifier.padding(16.dp).semantics { contentDescription = "Loading" }.testTag("skeleton"),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Skeleton(height = 22.dp, widthFraction = 0.6f)
        Skeleton(height = 120.dp)
        repeat(4) {
            Spacer(Modifier.height(6.dp))
            Skeleton(height = 12.dp, widthFraction = 0.5f)
            Skeleton(height = 18.dp, widthFraction = 0.85f)
            Skeleton(height = 12.dp, widthFraction = 0.95f)
        }
    }
}

/** The free server sleeps when idle; say so instead of a spinner with no explanation. */
@Composable
fun WakingPanel(modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    Row(
        modifier
            .fillMaxWidth()
            .padding(16.dp)
            .background(c.panel2, RoundedCornerShape(12.dp))
            .padding(16.dp)
            .semantics { liveRegion = LiveRegionMode.Polite }
            .testTag("waking"),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.5.dp, color = c.accent)
        Spacer(Modifier.width(14.dp))
        Column {
            Text("Waking the server, up to a minute", style = MaterialTheme.typography.titleSmall, color = c.text)
            Text(
                "The free server sleeps when nobody has used it for a while. Your field will open as soon as it answers.",
                style = MaterialTheme.typography.bodySmall,
                color = c.muted,
            )
        }
    }
}

fun LoadError.message(): Pair<String, String> = when (this) {
    LoadError.NoConnection -> "No connection" to "This phone is offline and nothing for this field is saved on it yet. Connect and try again."
    LoadError.NotAvailable -> "Not on the server yet" to "The server does not have this part for this field yet."
    LoadError.Server -> "The server didn't answer" to "It may still be waking up or busy. Try again in a moment."
}

@Composable
fun ErrorPanel(error: LoadError, onRetry: () -> Unit, modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    val (title, body) = error.message()
    Column(
        modifier
            .fillMaxWidth()
            .padding(16.dp)
            .background(c.panel2, RoundedCornerShape(12.dp))
            .padding(16.dp)
            .semantics { liveRegion = LiveRegionMode.Polite }
            .testTag("error"),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text(title, style = MaterialTheme.typography.titleMedium, color = c.bad)
        Text(body, style = MaterialTheme.typography.bodyMedium, color = c.text2)
        Spacer(Modifier.height(4.dp))
        PillButton("Try again", PillKind.Outline, onClick = onRetry)
    }
}

private val savedFormat = DateTimeFormatter.ofPattern("d MMM yyyy, h:mm a", Locale.UK)

fun savedOn(at: Instant): String = savedFormat.format(at.atZone(ZoneId.systemDefault())).replace("AM", "am").replace("PM", "pm")

/** "Saved on 14 Nov 2026, 4:38 pm. Can't reach the server right now." (the panel's one notice). */
@Composable
fun OfflineNote(savedAt: Instant, modifier: Modifier = Modifier) = Notice("Saved on ${savedOn(savedAt)}. Can't reach the server right now.", modifier.testTag("offline-note"))

/** Small hatched square: "not measured / example" across the product. */
@Composable
fun Hatch(modifier: Modifier = Modifier, color: Color = CropLyticsTheme.colors.muted) {
    androidx.compose.foundation.Canvas(modifier.border(1.dp, color)) {
        clipRect { drawHatch(color, 3.dp.toPx(), 1.dp.toPx()) }
    }
}
