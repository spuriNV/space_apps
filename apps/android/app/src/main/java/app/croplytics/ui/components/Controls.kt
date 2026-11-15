package app.croplytics.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.snap
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandHorizontally
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkHorizontally
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.unit.dp
import app.croplytics.ui.theme.CropLyticsTheme
import app.croplytics.ui.theme.LocalReduceMotion

/** Motion tokens (spec 6): standard easing, 120 / 180 / 240 / 320 ms; snap when the grower removed animations. */
val EaseStd = CubicBezierEasing(0.2f, 0f, 0f, 1f)
@Composable fun <T> motion(ms: Int) = if (LocalReduceMotion.current) snap<T>() else tween<T>(ms, easing = EaseStd)

/** A visible focus ring (2 dp accent) on every focusable control; put it before clickable. */
fun Modifier.focusRing(shape: Shape = CircleShape): Modifier = composed {
    var focused by remember { mutableStateOf(false) }
    val c = CropLyticsTheme.colors
    onFocusChanged { focused = it.isFocused }.then(if (focused) Modifier.border(2.dp, c.accent, shape) else Modifier)
}

enum class PillKind { Primary, Tonal, Outline, Text }

/** Buttons (spec 4.1): pills 44 dp tall; one filled primary per panel; scale .98 when pressed. */
@Composable
fun PillButton(label: String, kind: PillKind, modifier: Modifier = Modifier, icon: ImageVector? = null, small: Boolean = false, enabled: Boolean = true, onClick: () -> Unit) {
    val c = CropLyticsTheme.colors
    val src = remember { MutableInteractionSource() }
    val pressed by src.collectIsPressedAsState()
    val scale by animateFloatAsState(if (pressed && !LocalReduceMotion.current) 0.98f else 1f, motion(120), label = "press")
    val (bg, fg) = when {
        !enabled -> c.stateStrong to c.muted
        kind == PillKind.Primary -> c.accent to c.onAccent
        kind == PillKind.Tonal -> c.accentContainer to c.onAccentContainer
        kind == PillKind.Outline -> Color.Transparent to c.text
        else -> Color.Transparent to c.accent
    }
    Row(
        modifier.scale(scale).heightIn(min = if (small) 40.dp else 44.dp).clip(CircleShape).background(bg)
            .then(if (kind == PillKind.Outline) Modifier.border(1.dp, if (enabled) c.outline else c.line, CircleShape) else Modifier)
            .focusRing().clickable(src, androidx.compose.material3.ripple(), enabled = enabled, role = Role.Button, onClick = onClick)
            .padding(horizontal = if (kind == PillKind.Text) 12.dp else if (small) 16.dp else 20.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center,
    ) {
        if (icon != null) { Icon(icon, null, Modifier.size(18.dp), tint = fg); Spacer(Modifier.width(8.dp)) }
        Text(label, style = if (small) MaterialTheme.typography.labelMedium else MaterialTheme.typography.labelLarge, color = fg, maxLines = 1)
    }
}

/** Icon button (spec 4.2): a 40 dp neutral disc so Close is findable; 44 dp hit area. */
@Composable
fun IconDisc(description: String, modifier: Modifier = Modifier, icon: ImageVector = Icons.Filled.Close, ghost: Boolean = false, onClick: () -> Unit) {
    val c = CropLyticsTheme.colors
    Box(
        modifier.size(44.dp).padding(2.dp).clip(CircleShape).background(if (ghost) Color.Transparent else c.stateHover)
            .focusRing().clickable(role = Role.Button, onClick = onClick).semantics { contentDescription = description },
        contentAlignment = Alignment.Center,
    ) { Icon(icon, null, Modifier.size(20.dp), tint = c.text2) }
}

/** Filter chip (spec 4.3): outlined off; tonal container with a check that grows in when on. */
@Composable
fun FilterPill(label: String, selected: Boolean, modifier: Modifier = Modifier, count: Int? = null, onClick: () -> Unit) {
    val c = CropLyticsTheme.colors
    Row(
        modifier.heightIn(min = 44.dp).padding(vertical = 4.dp).clip(CircleShape)
            .background(if (selected) c.accentContainer else Color.Transparent)
            .then(if (selected) Modifier else Modifier.border(1.dp, c.outline, CircleShape))
            .focusRing().clickable(role = Role.Checkbox, onClick = onClick).semantics { this.selected = selected }
            .padding(start = if (selected) 12.dp else 16.dp, end = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        AnimatedVisibility(selected, enter = expandHorizontally(motion(180)) + fadeIn(motion(180)), exit = shrinkHorizontally(motion(180)) + fadeOut(motion(120))) {
            Row { Icon(Icons.Filled.Check, null, Modifier.size(16.dp), tint = c.accentOutline.takeIf { !selected } ?: c.onAccentContainer); Spacer(Modifier.width(6.dp)) }
        }
        Text(label, style = MaterialTheme.typography.labelMedium, color = if (selected) c.onAccentContainer else c.text2, modifier = Modifier.padding(vertical = 8.dp))
        if (count != null) Text("  $count", style = MaterialTheme.typography.bodySmall, color = if (selected) c.onAccentContainer else c.muted)
    }
}

/** Segmented control (spec 4.4): a raised paper thumb on a sunken pill track; never a green fill. */
@Composable
fun <T> Segmented(options: List<Pair<T, String>>, selected: T, modifier: Modifier = Modifier, label: String = "", onPick: (T) -> Unit) {
    val c = CropLyticsTheme.colors
    Row(
        modifier.horizontalScroll(rememberScrollState()).clip(CircleShape).background(c.panel2).border(1.dp, c.lineSoft, CircleShape).padding(3.dp)
            .semantics { if (label.isNotEmpty()) contentDescription = label },
        horizontalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        options.forEach { (v, text) ->
            val on = v == selected
            Box(
                Modifier.heightIn(min = 38.dp)
                    .then(if (on) Modifier.shadow(1.dp, CircleShape).background(c.raised, CircleShape) else Modifier)
                    .clip(CircleShape).focusRing().clickable(role = Role.RadioButton) { onPick(v) }.semantics { this.selected = on }
                    .padding(horizontal = 14.dp),
                contentAlignment = Alignment.Center,
            ) { Text(text, style = MaterialTheme.typography.labelMedium, color = if (on) c.text else c.text2, maxLines = 1) }
        }
    }
}

/** Section heading (spec 4.7): 22 sp slab, no rule; optional trailing text action and helper line. */
@Composable
fun SectionHead(text: String, modifier: Modifier = Modifier, helper: String? = null, action: Pair<String, () -> Unit>? = null) {
    val c = CropLyticsTheme.colors
    Column(modifier.fillMaxWidth().padding(start = 16.dp, end = 8.dp, top = 24.dp, bottom = 8.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(text, Modifier.weight(1f).semantics { heading() }, style = MaterialTheme.typography.titleLarge, color = c.text)
            action?.let { (l, go) -> PillButton(l, PillKind.Text, small = true, onClick = go) }
        }
        helper?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = c.muted) }
    }
}

/** The "More detail" disclosure (spec 4.8): a sunken 12 dp row, chevron turning over 180 ms. */
@Composable
fun MoreDetailRow(on: Boolean, teaser: String, modifier: Modifier = Modifier, onToggle: () -> Unit) {
    val c = CropLyticsTheme.colors
    val turn by animateFloatAsState(if (on) 180f else 0f, motion(180), label = "chevron")
    Row(
        modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp).heightIn(min = 56.dp).clip(RoundedCornerShape(12.dp)).background(c.panel2)
            .focusRing(RoundedCornerShape(12.dp)).clickable(role = Role.Button, onClickLabel = if (on) "Show less" else "Show more", onClick = onToggle)
            .semantics { stateDescription = if (on) "Expanded" else "Collapsed" }.padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(if (on) "Less detail" else "More detail", style = MaterialTheme.typography.labelLarge, color = c.accent)
            Text(if (on) "Back to the short version" else teaser, style = MaterialTheme.typography.bodySmall, color = c.muted)
        }
        Icon(Icons.Filled.KeyboardArrowDown, null, Modifier.size(20.dp).rotate(turn), tint = c.accent)
    }
}

/** Revealed detail fades in over 240 ms (opacity only: the content is long). */
@Composable
fun DetailReveal(visible: Boolean, content: @Composable () -> Unit) =
    AnimatedVisibility(visible, enter = fadeIn(motion(240)), exit = fadeOut(motion(120))) { Column { content() } }

/** The single "Example numbers" or offline notice per panel (spec 4.9). */
@Composable
fun Notice(text: String, modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    Row(modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp).clip(RoundedCornerShape(12.dp)).background(c.warnContainer).padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
        Hatch(Modifier.size(10.dp), c.onWarnContainer); Spacer(Modifier.width(8.dp))
        Text(text, style = MaterialTheme.typography.bodySmall.copy(fontStyle = FontStyle.Italic), color = c.onWarnContainer)
    }
}

/** A number that counts up to its value (spec motion: number count-up); the text keeps its unit. */
@Composable
fun CountUpText(text: String, style: androidx.compose.ui.text.TextStyle, color: Color, modifier: Modifier = Modifier) {
    val m = remember(text) { Regex("^(\\d+(?:\\.\\d+)?)(.*)$").find(text) }
    if (m == null || LocalReduceMotion.current) { Text(text, modifier, style = style, color = color); return }
    val target = m.groupValues[1].toFloat(); val decimals = m.groupValues[1].substringAfter('.', "").length
    var started by remember(text) { mutableStateOf(false) }
    val v by animateFloatAsState(if (started) target else 0f, tween(600, easing = EaseStd), label = "count")
    androidx.compose.runtime.LaunchedEffect(text) { started = true }
    Text(String.format(java.util.Locale.US, "%.${decimals}f", v) + m.groupValues[2], modifier.semantics { contentDescription = text }, style = style, color = color)
}
