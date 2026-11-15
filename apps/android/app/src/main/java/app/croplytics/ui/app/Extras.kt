package app.croplytics.ui.app

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import app.croplytics.data.repository.LoadState
import app.croplytics.domain.CatalogLogic
import app.croplytics.domain.CatalogPin
import app.croplytics.domain.DrawLogic
import app.croplytics.domain.WeekLogic
import app.croplytics.domain.WeekView
import app.croplytics.ui.components.FilterPill
import app.croplytics.ui.components.PillButton
import app.croplytics.ui.components.PillKind
import app.croplytics.ui.components.Skeleton
import app.croplytics.ui.components.focusRing
import app.croplytics.ui.theme.CropLyticsTheme
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb

// ---------------- This week ----------------

/** The "This week" card at the top of Field now. Hidden when the API has no week for this id. */
fun LazyListScope.thisWeekItem(week: LoadState<WeekView>) {
    if (week is LoadState.Failed) return
    item(key = "this-week") { ThisWeekCard(week) }
}

@Composable
fun ThisWeekCard(week: LoadState<WeekView>) {
    val c = CropLyticsTheme.colors
    Column(
        Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 6.dp).clip(RoundedCornerShape(16.dp)).background(c.raised)
            .border(1.dp, c.lineSoft, RoundedCornerShape(16.dp)).padding(16.dp).testTag("this-week"),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("This week", style = MaterialTheme.typography.titleMedium, color = c.text, modifier = Modifier.semantics { heading() })
        when (week) {
            is LoadState.Ready -> WeekBody(week.data, week.offline)
            LoadState.Waking -> Text("Waking the server, up to a minute.", style = MaterialTheme.typography.bodySmall, color = c.muted)
            else -> Column(Modifier.semantics { contentDescription = "Loading this week" }, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Skeleton(height = 18.dp, widthFraction = 0.7f); Skeleton(height = 44.dp); Skeleton(height = 14.dp)
            }
        }
    }
}

@Composable
private fun WeekBody(w: WeekView, offline: Boolean) {
    val c = CropLyticsTheme.colors
    var pick by remember { mutableStateOf<Int?>(null) }
    if (!w.hasAnything) { Text("The forecast is not available right now.", style = MaterialTheme.typography.bodyMedium, color = c.muted); return }
    if (w.label.isNotBlank()) Text(w.label, style = MaterialTheme.typography.labelSmall, color = c.muted)
    if (offline) Text("Showing the last copy saved on this phone.", style = MaterialTheme.typography.labelSmall, color = c.muted)
    // irrigation verdict and the 7-day need strip
    if (w.verdict.isNotBlank()) {
        Text(w.verdict, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold), color = c.text)
        if (w.kind == "irrigate" && w.acreInPerAcre != null) {
            val n = w.acreInPerAcre
            Text("${if (n < 0.05) "0" else String.format(java.util.Locale.US, "%.1f", n)} acre-inches per acre this week", style = MaterialTheme.typography.bodySmall, color = c.text2)
        }
        if (w.need.isNotEmpty()) {
            val peak = maxOf(0.01, w.need.maxOf { it.needIn })
            val spoken = "Daily water need: " + w.need.joinToString(", ") { "${it.dow} ${WeekLogic.inches(it.needIn * 25.4)} in" }
            Row(Modifier.fillMaxWidth().clearAndSetSemantics { contentDescription = spoken }, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                w.need.forEach { d ->
                    Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                        Box(Modifier.fillMaxWidth().height(44.dp), contentAlignment = Alignment.BottomCenter) {
                            Box(Modifier.fillMaxWidth().height((44 * maxOf(0.06, d.needIn / peak)).dp).clip(RoundedCornerShape(4.dp)).background(c.groundwater()))
                        }
                        Text(d.dow.take(2), style = MaterialTheme.typography.labelSmall, color = c.muted)
                    }
                }
            }
        }
        if (w.irrigationTag.isNotBlank()) Text(w.irrigationTag, style = MaterialTheme.typography.labelSmall, color = c.muted)
    }
    // field access chips and the "why"
    if (w.access.isNotEmpty()) {
        Text(w.accessLine, style = MaterialTheme.typography.bodyMedium, color = c.text)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            w.access.forEachIndexed { i, d ->
                val (bg, fg) = when (d.status) {
                    "ok" -> c.accentContainer to c.onAccentContainer
                    "marginal" -> c.warnContainer to c.onWarnContainer
                    "too_wet" -> c.bad.copy(alpha = 0.16f) to c.bad
                    else -> c.panel2 to c.muted
                }
                Column(
                    Modifier.weight(1f).heightIn(min = 48.dp).clip(RoundedCornerShape(12.dp)).background(bg)
                        .then(if (pick == i) Modifier.border(2.dp, c.accent, RoundedCornerShape(12.dp)) else Modifier)
                        .clickable(role = Role.Button) { pick = if (pick == i) null else i }.semantics { selected = pick == i; contentDescription = "${d.dow}: ${d.name}" }
                        .padding(vertical = 6.dp),
                    horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
                ) {
                    Text(d.dow, style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold), color = fg, maxLines = 1)
                    Text(d.word, style = MaterialTheme.typography.labelSmall, color = fg, maxLines = 1)
                }
            }
        }
        Text(
            pick?.let { w.access[it].let { d -> "${d.dow}: ${d.name}. ${d.why.ifBlank { "Nothing holds you back." }}" } }.orEmpty(),
            Modifier.semantics { liveRegion = LiveRegionMode.Polite }, style = MaterialTheme.typography.bodySmall, color = c.text2,
        )
        if (w.accessTag.isNotBlank()) Text(w.accessTag, style = MaterialTheme.typography.labelSmall, color = c.muted)
    }
    // the forecast row, in inches and degrees F
    if (w.forecast.isNotEmpty()) {
        Row(Modifier.fillMaxWidth().testTag("tw-forecast"), horizontalArrangement = Arrangement.spacedBy(2.dp)) {
            w.forecast.forEach { d ->
                Column(
                    Modifier.weight(1f).semantics(mergeDescendants = true) {
                        contentDescription = "${d.dow}: rain ${d.rainIn?.let { WeekLogic.inches(it * 25.4) } ?: "unknown"} inches, high ${d.hiF ?: "unknown"}, low ${d.loF ?: "unknown"} degrees"
                    },
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(d.dow, style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold), color = c.text)
                    Text(d.rainIn?.let { "${WeekLogic.inches(it * 25.4)}\"" } ?: "–", style = MaterialTheme.typography.labelSmall, color = c.groundwater())
                    Text(d.hiF?.let { "$it°" } ?: "–", style = MaterialTheme.typography.labelMedium, color = c.text)
                    Text(d.loF?.let { "$it°" } ?: "–", style = MaterialTheme.typography.labelSmall, color = c.muted)
                }
            }
        }
        Text("Rain in inches, then high and low in °F." + if (w.forecastTag.isNotBlank()) " ${w.forecastTag}" else "", style = MaterialTheme.typography.labelSmall, color = c.muted)
    }
    // alerts
    if (w.alerts.isNotEmpty()) {
        val uri = LocalUriHandler.current
        w.alerts.forEach { a ->
            Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(c.warnContainer).padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(a.title, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = c.onWarnContainer)
                Text("National Weather Service", Modifier.heightIn(min = 40.dp).clickable(role = Role.Button) { runCatching { uri.openUri(a.url) } }.padding(start = 8.dp, top = 10.dp),
                    style = MaterialTheme.typography.labelSmall.copy(textDecoration = TextDecoration.Underline), color = c.onWarnContainer)
            }
        }
    }
}

private fun app.croplytics.ui.theme.CropLyticsColors.groundwater() = app.croplytics.ui.theme.DataColors.groundwater

// ---------------- A tapped spot: the loading line ----------------

@Composable
fun SpotLine(msg: SpotMsg, onDismiss: () -> Unit, modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    Row(
        modifier.shadow(6.dp, CircleShape).clip(CircleShape).background(c.raised).padding(start = 16.dp, end = 6.dp, top = 6.dp, bottom = 6.dp).semantics { liveRegion = LiveRegionMode.Polite }.testTag("spot-line"),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (!msg.isError) CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp, color = c.accent) else Spacer(Modifier.width(0.dp))
        Text(msg.text, Modifier.padding(horizontal = 10.dp, vertical = 6.dp), style = MaterialTheme.typography.bodySmall, color = if (msg.isError) c.bad else c.text)
        PillButton(if (msg.isError) "OK" else "Cancel", PillKind.Text, small = true, onClick = onDismiss)
    }
}

// ---------------- Draw a field ----------------

@Composable
fun DrawBar(d: DrawState, onUndo: () -> Unit, onCancel: () -> Unit, onSave: (String) -> Unit, modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    var name by remember { mutableStateOf("My field") }
    Column(
        modifier.padding(horizontal = 12.dp).fillMaxWidth().shadow(8.dp, RoundedCornerShape(20.dp)).clip(RoundedCornerShape(20.dp)).background(c.paper).padding(14.dp).testTag("draw-bar"),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("Draw your field", style = MaterialTheme.typography.titleSmall, color = c.text, modifier = Modifier.semantics { heading() })
        val n = d.points.size
        Text(
            when { n == 0 -> "Tap each corner of the field on the map."; n < 3 -> "$n corner${if (n == 1) "" else "s"}. Tap at least 3."; else -> "$n corners, about ${String.format(java.util.Locale.US, "%.0f", DrawLogic.acres(d.points))} acres." },
            style = MaterialTheme.typography.bodySmall, color = c.text2, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
        )
        d.error?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = c.bad) }
        if (n >= 3) SearchPill(name, { name = it.take(60) }, "Name your field", Modifier.testTag("draw-name"))
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            PillButton("Undo", PillKind.Outline, small = true, enabled = n > 0 && !d.saving, onClick = onUndo)
            PillButton("Cancel", PillKind.Outline, small = true, onClick = onCancel)
            PillButton(if (d.saving) "Saving, a few seconds" else "Save field", PillKind.Primary, small = true, enabled = n >= 3 && !d.saving, modifier = Modifier.testTag("draw-save")) { onSave(name) }
        }
    }
}

// ---------------- Farm catalog in search ----------------

/** Crop chips and the matching farms (the web's catalog group). */
fun LazyListScope.catalogSearch(state: MainUiState, onCrop: (String) -> Unit, onOpen: (CatalogPin) -> Unit) {
    val cat = state.catalog ?: return
    if (cat.groups.isEmpty()) return
    item(key = "cat-chips") {
        val c = CropLyticsTheme.colors
        Column(Modifier.padding(horizontal = 16.dp)) {
            Text("Farms across the US and Canada", style = MaterialTheme.typography.labelMedium, color = c.muted, modifier = Modifier.padding(top = 4.dp).semantics { heading() })
            Row(Modifier.horizontalScroll(rememberScrollState()).padding(vertical = 2.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                cat.groups.forEach { g -> FilterPill(g.label, state.crop == g.key, Modifier.testTag("crop-${g.key}"), count = g.count) { onCrop(g.key) } }
            }
        }
    }
    val rows = state.catalogShown
    items(rows, key = { "cat-${it.id}" }) { p ->
        val c = CropLyticsTheme.colors
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 8.dp).clip(RoundedCornerShape(12.dp)).focusRing(RoundedCornerShape(12.dp)).clickable(role = Role.Button, onClickLabel = "Open this farm") { onOpen(p) }.padding(12.dp).testTag("cat-${p.id}"),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.size(28.dp).clip(CircleShape).background(Color(android.graphics.Color.parseColor(CatalogLogic.color(p.group)))), contentAlignment = Alignment.Center) {
                Text(CatalogLogic.letter(p.group), style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = Color(0xFF191C16))
            }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(p.name, style = MaterialTheme.typography.titleSmall, color = c.text)
                Text(listOfNotNull(p.groupLabel.takeIf { it.isNotBlank() }, p.county.takeIf { it.isNotBlank() }, p.acres?.let { "${it.toInt()} acres" }).joinToString(" · "), style = MaterialTheme.typography.bodySmall, color = c.muted)
            }
        }
    }
    if (state.crop != null || state.query.isNotBlank()) if (rows.isEmpty()) item(key = "cat-none") { Text("No farm matches.", Modifier.padding(16.dp), color = CropLyticsTheme.colors.muted, style = MaterialTheme.typography.bodyMedium) }
}

// ---------------- Ask CropLytics ----------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AskSheet(a: AskUi, fieldName: String?, onAsk: (String) -> Unit, onDismiss: () -> Unit) {
    val c = CropLyticsTheme.colors
    var q by remember { mutableStateOf("") }
    val suggestions = if (fieldName != null) listOf("Do I need to irrigate this week?", "Is the field too wet to work?", "What should I plant next?") else listOf("Which crops grow near here?", "How wet was this winter?", "How do I compare rotations?")
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true), containerColor = c.paper) {
        Column(Modifier.padding(horizontal = 16.dp).navigationBarsPadding().testTag("ask-sheet")) {
            Text("Ask CropLytics", style = MaterialTheme.typography.titleMedium, color = c.text, modifier = Modifier.semantics { heading() })
            Text(if (fieldName != null) "About $fieldName. Answers can be wrong; check with your adviser." else "Answers can be wrong; check with your adviser.", style = MaterialTheme.typography.bodySmall, color = c.muted, modifier = Modifier.padding(bottom = 8.dp))
            LazyColumn(Modifier.fillMaxWidth().heightIn(max = 380.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (a.turns.isEmpty() && !a.busy) item(key = "sug") {
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) { suggestions.forEach { s -> PillButton(s, PillKind.Tonal, small = true) { onAsk(s) } } }
                }
                items(a.turns.size, key = { "turn-$it" }) { i ->
                    val (role, text) = a.turns[i]
                    val mine = role == "user"
                    Box(Modifier.fillMaxWidth(), contentAlignment = if (mine) Alignment.CenterEnd else Alignment.CenterStart) {
                        Text(text, Modifier.clip(RoundedCornerShape(16.dp)).background(if (mine) c.accentContainer else c.raised).border(if (mine) 0.dp else 1.dp, c.lineSoft, RoundedCornerShape(16.dp)).padding(12.dp),
                            style = MaterialTheme.typography.bodyMedium, color = if (mine) c.onAccentContainer else c.text, textAlign = TextAlign.Start)
                    }
                }
                if (a.busy) item(key = "busy") { Text("Thinking…", Modifier.semantics { liveRegion = LiveRegionMode.Polite }, style = MaterialTheme.typography.bodySmall, color = c.muted) }
                a.error?.let { e -> item(key = "err") { Text(e, Modifier.semantics { liveRegion = LiveRegionMode.Polite }, style = MaterialTheme.typography.bodySmall, color = c.bad) } }
            }
            Row(Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                SearchPill(q, { q = it.take(300) }, "Type your question", Modifier.weight(1f).testTag("ask-input"))
                PillButton("Ask", PillKind.Primary, enabled = q.isNotBlank() && !a.busy, modifier = Modifier.testTag("ask-send")) { onAsk(q); q = "" }
            }
        }
    }
}
