package app.croplytics.ui.app

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.croplytics.domain.BC
import app.croplytics.domain.Gloss
import app.croplytics.domain.Map3D
import app.croplytics.domain.MapDatasets
import app.croplytics.domain.Sources
import app.croplytics.domain.Timeline
import app.croplytics.ui.components.Hatch
import app.croplytics.ui.map.hexColor
import app.croplytics.ui.theme.CropLyticsTheme
import kotlin.math.log10
import kotlin.math.sqrt

/** Solid paper top bar (web phone layout): wordmark, field switcher, then the "Viewing" date and Map layers. 3 dp spot-green band under it. */
@Composable
fun TopBar(state: MainUiState, onHome: () -> Unit, onSwitch: () -> Unit, onDate: () -> Unit, onLayers: () -> Unit) {
    val c = CropLyticsTheme.colors
    val sel = state.selected
    Column(Modifier.fillMaxWidth().background(c.paper).statusBarsPadding().testTag("topbar")) {
        Row(Modifier.fillMaxWidth().padding(start = 12.dp, end = 8.dp, top = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(
                "CropLytics",
                Modifier.clickable(role = Role.Button, onClickLabel = "Back to all of California", onClick = onHome).padding(vertical = 8.dp).semantics { heading() },
                style = MaterialTheme.typography.titleLarge, color = c.accent,
            )
            Spacer(Modifier.width(12.dp))
            Row(
                Modifier.weight(1f).clickable(role = Role.Button, onClickLabel = "Change field", onClick = onSwitch).padding(vertical = 4.dp).testTag("field-switch"),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(sel?.let { "${it.id.county} County, ${it.id.acres} acres" } ?: "No field picked", style = MaterialTheme.typography.labelSmall, color = c.muted, maxLines = 1)
                    Text(sel?.id?.name ?: "Pick your field", style = MaterialTheme.typography.titleSmall, color = c.text, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                Icon(Icons.Filled.KeyboardArrowDown, contentDescription = null, tint = c.muted)
            }
        }
        Row(Modifier.fillMaxWidth().padding(start = 12.dp, end = 12.dp, bottom = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Chip("Viewing", if (state.isToday) "Today, ${Timeline.when_(state.t)}" else Timeline.label(state.t), Modifier.weight(1f).testTag("date-control"), onDate)
            Chip(null, "Map layers", Modifier.testTag("layers-btn"), onLayers)
        }
        HorizontalDivider(color = c.line)
        Box(Modifier.fillMaxWidth().height(3.dp).background(c.headBand))
    }
}

@Composable
private fun Chip(small: String?, label: String, modifier: Modifier, onClick: () -> Unit) {
    val c = CropLyticsTheme.colors
    Row(
        modifier.border(1.dp, c.line, RoundedCornerShape(3.dp)).clickable(role = Role.Button, onClick = onClick).heightIn(min = 40.dp).padding(horizontal = 10.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (small != null) { Text(small, style = MaterialTheme.typography.labelSmall, color = c.muted); Spacer(Modifier.width(6.dp)) }
        Text(label, Modifier.weight(1f, fill = false), style = MaterialTheme.typography.labelLarge, color = c.text, maxLines = 1, overflow = TextOverflow.Ellipsis)
        if (small != null) Icon(Icons.Filled.KeyboardArrowDown, null, tint = c.muted, modifier = Modifier.size(18.dp))
    }
}

/** "Showing mid Jul 2022 · Back to today" when the viewing date is not today. */
@Composable
fun DateBanner(t: Int, onToday: () -> Unit) {
    val c = CropLyticsTheme.colors
    Row(Modifier.fillMaxWidth().background(c.panel2).padding(horizontal = 12.dp, vertical = 4.dp).testTag("date-banner"), verticalAlignment = Alignment.CenterVertically) {
        Text("Showing ${Timeline.label(t)}", Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = c.text)
        TextButton(onClick = onToday) { Text("Back to today", color = c.accent) }
    }
}

/** The sections as text tabs at the bottom (web mob-tabs): Now, Season, Year, Compare, Print. Disabled until a field is picked. */
@Composable
fun BottomTabs(selected: Tab?, enabled: Boolean, onTab: (Tab) -> Unit) {
    val c = CropLyticsTheme.colors
    Column(Modifier.fillMaxWidth().background(c.paper).navigationBarsPadding()) {
        HorizontalDivider(color = c.line)
        Row(Modifier.fillMaxWidth().height(IntrinsicSize.Min)) {
            Tab.entries.forEach { t ->
                val on = t == selected
                Column(
                    Modifier.weight(1f).fillMaxHeight()
                        .clickable(enabled = enabled, role = Role.Tab) { onTab(t) }
                        .semantics { this.selected = on }
                        .testTag("mtab-${t.name}"),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Box(Modifier.fillMaxWidth().height(3.dp).background(if (on) c.accent else c.paper))
                    Text(
                        t.short, Modifier.padding(vertical = 12.dp), style = MaterialTheme.typography.labelLarge,
                        color = when { !enabled -> c.muted.copy(alpha = 0.5f); on -> c.text; else -> c.muted }, maxLines = 1,
                    )
                }
            }
        }
    }
}

/** Field switcher (web tb-menu): search every field, British Columbia, and back to the whole state. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FieldSwitcher(state: MainUiState, onPick: (String) -> Unit, onBC: () -> Unit, onHome: () -> Unit, onDismiss: () -> Unit) {
    val c = CropLyticsTheme.colors
    var q by rememberSaveable { mutableStateOf("") }
    data class Item(val key: String, val title: String, val sub: String, val go: () -> Unit)
    val items = state.fields.let { s -> (s as? app.croplytics.data.repository.LoadState.Ready)?.data.orEmpty() }.map { f ->
        Item(f.id.id, f.id.name, "${f.id.county} County · ${f.id.acres} acres${f.id.stateFieldNo?.let { " · state field no. $it" } ?: ""}") { onPick(f.id.id) }
    } + Item("bc", "Sumas Prairie, British Columbia", "Not set up yet: why", onBC) + Item("ca", "California", "Back to the whole state", onHome)
    val shown = items.filter { q.isBlank() || (it.title + it.sub).lowercase().contains(q.trim().lowercase()) }
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true), containerColor = c.paper) {
        Column(Modifier.padding(horizontal = 16.dp).testTag("field-menu")) {
            OutlinedTextField(
                q, { q = it }, Modifier.fillMaxWidth().testTag("search"), placeholder = { Text("Find a field by town, county or crop") },
                leadingIcon = { Icon(Icons.Filled.Search, null) }, singleLine = true, shape = RoundedCornerShape(3.dp),
                colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = c.accent, unfocusedBorderColor = c.line),
            )
            LazyColumn(Modifier.fillMaxWidth().heightIn(max = 520.dp).navigationBarsPadding()) {
                items(shown, key = { it.key }) { it ->
                    Column(Modifier.fillMaxWidth().clickable { it.go(); onDismiss() }.background(if (it.key == state.selectedId) c.panel2 else c.paper).padding(vertical = 10.dp).testTag("switch-${it.key}")) {
                        Text(it.title, style = MaterialTheme.typography.titleSmall, color = c.text)
                        Text(it.sub, style = MaterialTheme.typography.bodySmall, color = c.muted)
                    }
                    HorizontalDivider(color = c.lineSoft)
                }
                if (shown.isEmpty()) item { Text("No field matches.", Modifier.padding(16.dp), color = c.muted) }
            }
        }
    }
}

/** The "Viewing" date control: quick picks, a month picker 2023 to now (earlier years on request), back to today. */
@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun DateSheet(state: MainUiState, quick: List<QuickDate>, years: List<Int>, onPick: (Int) -> Unit, onEarlier: () -> Unit, onDismiss: () -> Unit) {
    val c = CropLyticsTheme.colors
    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = c.paper) {
        Column(Modifier.padding(horizontal = 16.dp).verticalScroll(rememberScrollState()).navigationBarsPadding().testTag("date-pop")) {
            Text("Viewing", style = MaterialTheme.typography.titleMedium, color = c.text)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 8.dp)) {
                quick.forEach { q ->
                    val on = state.t == q.t
                    Column(
                        Modifier.border(1.dp, if (on) c.accent else c.line, RoundedCornerShape(3.dp)).background(if (on) c.accent else c.paper, RoundedCornerShape(3.dp))
                            .clickable { onPick(q.t); onDismiss() }.padding(horizontal = 12.dp, vertical = 6.dp),
                    ) {
                        Text(q.label, style = MaterialTheme.typography.labelLarge, color = if (on) c.onAccent else c.text)
                        Text(q.sub, style = MaterialTheme.typography.labelSmall, color = if (on) c.onAccent else c.muted)
                    }
                }
            }
            years.filter { state.showEarlier || it >= Timeline.RECENT_FROM }.reversed().forEach { y ->
                Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("$y", Modifier.width(48.dp), style = MaterialTheme.typography.labelLarge, color = c.text)
                    FlowRow(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(4.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Timeline.MONTHS.forEachIndexed { k, m ->
                            val tt = Timeline.tOf(y, k * 3 + 1); val future = tt > state.todayT
                            val on = Timeline.yearOf(state.t) == y && Timeline.stepOf(state.t) / 3 == k
                            Text(
                                m, Modifier.border(1.dp, if (on) c.accent else c.lineSoft, RoundedCornerShape(2.dp)).background(if (on) c.accent else c.paper)
                                    .clickable(enabled = !future) { onPick(tt); onDismiss() }.padding(horizontal = 7.dp, vertical = 6.dp),
                                style = MaterialTheme.typography.labelMedium, color = if (future) c.muted.copy(alpha = 0.4f) else if (on) c.onAccent else c.text,
                            )
                        }
                    }
                }
            }
            Row {
                TextButton(onClick = onEarlier) { Text(if (state.showEarlier) "Hide earlier years" else "Show earlier years (2016–2022)", color = c.accent) }
                if (!state.isToday) TextButton(onClick = { onPick(state.todayT); onDismiss() }) { Text("Back to today", color = c.accent) }
            }
            Spacer(Modifier.height(16.dp))
        }
    }
}

/** Map layers (Panels.tsx LayersDrawer): what each dataset sees, its pixel size against this field, and a log-scale ruler. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LayersSheet(on: Map<String, Boolean>, areaHa: Double?, onToggle: (String) -> Unit, onDismiss: () -> Unit) {
    val c = CropLyticsTheme.colors
    val fieldHa = areaHa ?: 60.0
    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = c.paper) {
        Column(Modifier.padding(horizontal = 16.dp).verticalScroll(rememberScrollState()).navigationBarsPadding().testTag("layers-drawer")) {
            Text("Layers", style = MaterialTheme.typography.titleLarge, color = c.text)
            Text("NASA Earth data", style = MaterialTheme.typography.bodySmall, color = c.muted)
            listOf(false to ("Sees inside your field" to "pixel smaller than the field"), true to ("Sees your district or basin" to "one pixel covers many fields")).forEach { (regional, titles) ->
                Spacer(Modifier.height(10.dp))
                Text(titles.first, style = MaterialTheme.typography.titleSmall, color = c.text); Text(titles.second, style = MaterialTheme.typography.labelSmall, color = c.muted)
                MapDatasets.ALL.filter { it.regional == regional }.forEach { d ->
                    Row(Modifier.fillMaxWidth().clickable { onToggle(d.id) }.padding(vertical = 6.dp).testTag("layer-${d.id}"), verticalAlignment = Alignment.Top) {
                        Checkbox(on[d.id] == true, { onToggle(d.id) }, colors = CheckboxDefaults.colors(checkedColor = hexColor(d.color), checkmarkColor = c.text))
                        Column(Modifier.weight(1f)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(d.name, style = MaterialTheme.typography.labelLarge, color = c.text)
                                Spacer(Modifier.width(6.dp))
                                Text(d.nativeScale, Modifier.border(1.dp, hexColor(d.color), RoundedCornerShape(2.dp)).padding(horizontal = 4.dp), style = MaterialTheme.typography.labelSmall, color = c.text)
                            }
                            Text(d.sees, style = MaterialTheme.typography.bodySmall, color = c.text2)
                            Text("${Map3D.pixelRatio(d, fieldHa)} · ${d.cadence} · since ${d.since}${d.inStack?.let { " · in 3D stack: $it" } ?: ""}", style = MaterialTheme.typography.labelSmall, color = c.muted)
                            d.caveat?.let { Text(it, style = MaterialTheme.typography.labelSmall.copy(fontStyle = FontStyle.Italic), color = c.warn) }
                        }
                    }
                }
            }
            Spacer(Modifier.height(10.dp))
            Text("Pixel size, to scale (log)", style = MaterialTheme.typography.titleSmall, color = c.text)
            val fieldKm = sqrt(fieldHa / 100)
            (MapDatasets.ALL.map { Triple(it.name, (8 + log10(it.footprintM / 30) * 30).toFloat(), it.color to it.nativeScale) } +
                Triple("Your field", (8 + log10(fieldKm * 1000 / 30) * 30).toFloat(), "#191c16" to "≈ ${String.format(java.util.Locale.US, "%.1f", fieldKm)} km")).forEach { (name, w, cs) ->
                Row(Modifier.fillMaxWidth().padding(vertical = 2.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(name, Modifier.width(84.dp), style = MaterialTheme.typography.labelSmall, color = c.text2)
                    Box(Modifier.weight(1f)) { Box(Modifier.fillMaxWidth((w / 100f).coerceIn(0.02f, 1f)).height(8.dp).background(hexColor(cs.first))) }
                    Text(cs.second, Modifier.width(64.dp).padding(start = 6.dp), style = MaterialTheme.typography.labelSmall, color = c.muted)
                }
            }
            Text("Coarse satellites describe weeks and years across the valley. They cannot tell one field from its neighbour.", Modifier.padding(vertical = 12.dp), style = MaterialTheme.typography.bodySmall, color = c.muted)
        }
    }
}

/** "Why not BC yet" (Panels.tsx BCCard). */
@Composable
fun BCCard(onClose: () -> Unit) {
    val c = CropLyticsTheme.colors
    Column(Modifier.fillMaxWidth().padding(16.dp).testTag("bc-card"), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Hatch(Modifier.size(11.dp), c.warn); Spacer(Modifier.width(6.dp))
            Text("Out of scope for now", Modifier.weight(1f), style = MaterialTheme.typography.labelMedium, color = c.warn)
            TextButton(onClick = onClose) { Text("Close", color = c.accent) }
        }
        Text(BC.TITLE, style = MaterialTheme.typography.titleLarge, color = c.text)
        Text(BC.INTRO, style = MaterialTheme.typography.bodyMedium, color = c.text2)
        BC.LINES.forEach { (l, t) -> Column { Text(l, style = MaterialTheme.typography.labelLarge, color = c.text); Text(t, style = MaterialTheme.typography.bodySmall, color = c.text2) } }
        Text(BC.LIMIT, style = MaterialTheme.typography.bodySmall, color = c.muted)
        Text("${BC.NEXT} (${BC.NEXT_REF})", style = MaterialTheme.typography.labelMedium, color = c.accent)
    }
}

/** Sources (Sources.tsx). */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SourcesSheet(onDismiss: () -> Unit) {
    val c = CropLyticsTheme.colors
    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = c.paper) {
        Column(Modifier.padding(horizontal = 16.dp).verticalScroll(rememberScrollState()).navigationBarsPadding().testTag("sources")) {
            Text("Sources", style = MaterialTheme.typography.titleLarge, color = c.text)
            Sources.GROUPS.forEach { (g, items) ->
                Spacer(Modifier.height(10.dp)); Text(g, style = MaterialTheme.typography.titleSmall, color = c.text)
                items.forEach { (n, d) -> Column(Modifier.padding(vertical = 4.dp)) { Text(n, style = MaterialTheme.typography.labelLarge, color = c.text); Text(d, style = MaterialTheme.typography.bodySmall, color = c.text2) } }
            }
            Text(Sources.FOOT, Modifier.padding(vertical = 14.dp), style = MaterialTheme.typography.bodySmall, color = c.muted)
        }
    }
}

/** "What's this?" opens a plain explanation in place (What.tsx); the API glossary text wins when served. */
@Composable
fun What(g: Gloss, api: Map<String, Pair<String, String>>) {
    val c = CropLyticsTheme.colors
    var open by remember { mutableStateOf(false) }
    val (term, text) = api[g.apiKey] ?: (g.term to g.text)
    Column {
        Text(
            if (open) "Close" else "What’s this?",
            Modifier.clickable(role = Role.Button) { open = !open }.padding(vertical = 6.dp),
            style = MaterialTheme.typography.labelMedium.copy(textDecoration = TextDecoration.Underline), color = c.accent,
        )
        if (open) Text("$term. $text", Modifier.background(c.panel2).padding(8.dp), style = MaterialTheme.typography.bodySmall, color = c.text)
    }
}

/** The one "More detail" switch for the whole app (Detail.tsx). */
@Composable
fun MoreDetailButton(on: Boolean, what: String, onToggle: () -> Unit) {
    val c = CropLyticsTheme.colors
    Column(
        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp).border(1.dp, if (on) c.accent else c.line, RoundedCornerShape(3.dp))
            .clickable(role = Role.Button, onClickLabel = if (on) "Show less" else "Show more") { onToggle() }.padding(12.dp).testTag("more-detail"),
    ) {
        Text(if (on) "Less detail" else "More detail", style = MaterialTheme.typography.labelLarge, color = c.accent)
        Text(if (on) "Back to the short version" else what, style = MaterialTheme.typography.bodySmall, color = c.muted)
    }
}
