package app.croplytics.ui.app

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.layout.offset
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import app.croplytics.ui.components.DetailReveal
import app.croplytics.ui.components.IconDisc
import app.croplytics.ui.components.MoreDetailRow
import app.croplytics.ui.components.PillButton
import app.croplytics.ui.components.PillKind
import app.croplytics.ui.components.focusRing
import app.croplytics.ui.components.motion
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
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Clear
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

/** Paper top bar (web phone layout): wordmark, field switcher, menu holding Viewing and Map layers; 3 dp green band under it. */
@Composable
fun TopBar(state: MainUiState, onHome: () -> Unit, onSwitch: () -> Unit, onDate: () -> Unit, onLayers: () -> Unit) {
    val c = CropLyticsTheme.colors
    val sel = state.selected
    var menu by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxWidth().background(c.paper).statusBarsPadding().testTag("topbar")) {
        Row(Modifier.fillMaxWidth().heightIn(min = 56.dp).padding(start = 12.dp, end = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(
                "CropLytics",
                Modifier.clip(RoundedCornerShape(8.dp)).focusRing(RoundedCornerShape(8.dp)).clickable(role = Role.Button, onClickLabel = "Back to all of California", onClick = onHome)
                    .padding(horizontal = 4.dp, vertical = 8.dp).semantics { heading() },
                style = MaterialTheme.typography.titleLarge, color = c.accent,
            )
            Spacer(Modifier.width(8.dp))
            Box(Modifier.width(1.dp).height(32.dp).background(c.line))
            Row(
                Modifier.weight(1f).clip(RoundedCornerShape(12.dp)).focusRing(RoundedCornerShape(12.dp)).clickable(role = Role.Button, onClickLabel = "Change field", onClick = onSwitch)
                    .padding(horizontal = 10.dp, vertical = 6.dp).testTag("field-switch"),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(sel?.let { "${it.id.place}, ${it.id.acres} acres" } ?: "No field picked", style = MaterialTheme.typography.labelSmall, color = c.muted, maxLines = 1)
                    Text(sel?.id?.name ?: "Pick your field", style = MaterialTheme.typography.titleSmall, color = c.text, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                Icon(Icons.Filled.KeyboardArrowDown, contentDescription = null, tint = c.muted)
            }
            Box {
                IconDisc("Menu: viewing date and map layers", icon = Icons.Filled.Menu, ghost = true, modifier = Modifier.testTag("menu")) { menu = true }
                DropdownMenu(menu, { menu = false }, shape = RoundedCornerShape(16.dp), containerColor = c.raised, shadowElevation = 12.dp) {
                    DropdownMenuItem(
                        text = { Column { Text("Viewing", style = MaterialTheme.typography.labelSmall, color = c.muted); Text(if (state.isToday) "Today, ${Timeline.when_(state.t)}" else Timeline.label(state.t), style = MaterialTheme.typography.labelLarge, color = c.text) } },
                        onClick = { menu = false; onDate() }, modifier = Modifier.testTag("date-control"),
                    )
                    DropdownMenuItem(text = { Text("Map layers", style = MaterialTheme.typography.labelLarge, color = c.text) }, onClick = { menu = false; onLayers() }, modifier = Modifier.testTag("layers-btn"))
                }
            }
        }
        Box(Modifier.fillMaxWidth().height(3.dp).background(c.headBand))
    }
}

/** "Showing mid Jul 2022 · Back to today": a pill floating over the map when the viewing date is not today. */
@Composable
fun DateBanner(t: Int, onToday: () -> Unit, modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    Row(
        modifier.shadow(6.dp, CircleShape).clip(CircleShape).background(c.raised).padding(start = 16.dp, end = 4.dp).testTag("date-banner"),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("Showing ${Timeline.label(t)}", style = MaterialTheme.typography.labelMedium, color = c.text)
        PillButton("Back to today", PillKind.Text, small = true, onClick = onToday)
    }
}

/** The sections at the bottom (spec 4.11): 64 dp, the active label inside a tonal pill; disabled until a field is picked. */
@Composable
fun BottomTabs(selected: Tab?, enabled: Boolean, onTab: (Tab) -> Unit) {
    val c = CropLyticsTheme.colors
    Column(Modifier.fillMaxWidth().background(c.paper).navigationBarsPadding()) {
        Box(Modifier.fillMaxWidth().height(1.dp).background(c.line))
        Row(Modifier.fillMaxWidth().height(64.dp).padding(horizontal = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            Tab.entries.forEach { t ->
                val on = t == selected
                val bg by animateColorAsState(if (on) c.accentContainer else Color.Transparent, motion(180), label = "tab")
                Box(
                    Modifier.weight(1f).heightIn(min = 48.dp).clip(CircleShape).focusRing().clickable(enabled = enabled, role = Role.Tab) { onTab(t) }
                        .semantics { this.selected = on }.testTag("mtab-${t.name}"),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        t.short, Modifier.clip(CircleShape).background(bg).padding(horizontal = 6.dp, vertical = 6.dp), softWrap = false,
                        style = MaterialTheme.typography.labelMedium, maxLines = 1,
                        color = when { !enabled -> c.muted.copy(alpha = 0.45f); on -> c.onAccentContainer; else -> c.text2 },
                    )
                }
            }
        }
    }
}

/** Pill search field (spec 4.12): sunken fill, raised with a green ring while typing. */
@Composable
fun SearchPill(value: String, onValue: (String) -> Unit, placeholder: String, modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    var focused by remember { mutableStateOf(false) }
    Row(
        modifier.fillMaxWidth().heightIn(min = 48.dp).clip(CircleShape).background(if (focused) c.raised else c.panel2)
            .border(if (focused) 2.dp else 1.dp, if (focused) c.accent else c.lineSoft, CircleShape).padding(start = 16.dp, end = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Filled.Search, null, Modifier.size(18.dp), tint = c.muted)
        Spacer(Modifier.width(10.dp))
        Box(Modifier.weight(1f)) {
            if (value.isEmpty()) Text(placeholder, style = MaterialTheme.typography.bodyMedium, color = c.muted, maxLines = 1)
            BasicTextField(value, onValue, Modifier.fillMaxWidth().onFocusChanged { focused = it.isFocused }, singleLine = true,
                textStyle = MaterialTheme.typography.bodyMedium.copy(color = c.text), cursorBrush = SolidColor(c.accent))
        }
        if (value.isNotEmpty()) IconDisc("Clear search", icon = Icons.Filled.Clear, ghost = true) { onValue("") }
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
            SearchPill(q, { q = it }, "Find a field by town, county or crop", Modifier.testTag("search"))
            LazyColumn(Modifier.fillMaxWidth().heightIn(max = 520.dp).navigationBarsPadding()) {
                items(shown, key = { it.key }) { it ->
                    Column(Modifier.fillMaxWidth().padding(vertical = 1.dp).clip(RoundedCornerShape(12.dp)).background(if (it.key == state.selectedId) c.accentContainer else Color.Transparent).clickable { it.go(); onDismiss() }.padding(12.dp).testTag("switch-${it.key}")) {
                        Text(it.title, style = MaterialTheme.typography.titleSmall, color = c.text)
                        Text(it.sub, style = MaterialTheme.typography.bodySmall, color = c.muted)
                    }
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
                        Modifier.clip(RoundedCornerShape(16.dp)).background(if (on) c.accentContainer else Color.Transparent)
                            .then(if (on) Modifier else Modifier.border(1.dp, c.outline, RoundedCornerShape(16.dp)))
                            .focusRing(RoundedCornerShape(16.dp)).clickable { onPick(q.t); onDismiss() }.padding(horizontal = 14.dp, vertical = 8.dp),
                    ) {
                        Text(q.label, style = MaterialTheme.typography.labelMedium, color = if (on) c.onAccentContainer else c.text)
                        Text(q.sub, style = MaterialTheme.typography.labelSmall, color = if (on) c.onAccentContainer else c.muted)
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
                                m, Modifier.clip(CircleShape).background(if (on) c.accentContainer else Color.Transparent)
                                    .clickable(enabled = !future) { onPick(tt); onDismiss() }.heightIn(min = 36.dp).padding(horizontal = 9.dp, vertical = 8.dp),
                                style = MaterialTheme.typography.labelMedium, color = if (future) c.muted.copy(alpha = 0.4f) else if (on) c.onAccentContainer else c.text,
                            )
                        }
                    }
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 8.dp)) {
                PillButton(if (state.showEarlier) "Hide earlier years" else "Show earlier years (2016–2022)", PillKind.Outline, small = true, onClick = onEarlier)
                if (!state.isToday) PillButton("Back to today", PillKind.Outline, small = true) { onPick(state.todayT); onDismiss() }
            }
            Spacer(Modifier.height(16.dp))
        }
    }
}

/** Map layers (Panels.tsx LayersDrawer): what each dataset sees, its pixel size against this field, and a log-scale ruler. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LayersSheet(on: Map<String, Boolean>, areaHa: Double?, onToggle: (String) -> Unit, showReserves: Boolean = false, onDismiss: () -> Unit) {
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
            if (showReserves) {
                Spacer(Modifier.height(10.dp))
                Text("Context", style = MaterialTheme.typography.titleSmall, color = c.text); Text("BC only, off unless you turn it on", style = MaterialTheme.typography.labelSmall, color = c.muted)
                Row(Modifier.fillMaxWidth().clickable { onToggle("reserves") }.padding(vertical = 6.dp).testTag("layer-reserves"), verticalAlignment = Alignment.Top) {
                    Checkbox(on["reserves"] == true, { onToggle("reserves") })
                    Column(Modifier.weight(1f)) {
                        Text("Reserve boundaries (context)", style = MaterialTheme.typography.labelLarge, color = c.text)
                        Text("Indian reserve outlines near this field, with their names.", style = MaterialTheme.typography.bodySmall, color = c.text2)
                        Text("For context only. Not part of the analysis.", style = MaterialTheme.typography.labelSmall, color = c.muted)
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
            IconDisc("Close", onClick = onClose)
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
        PillButton(if (open) "Close" else "What’s this?", PillKind.Text, small = true, modifier = Modifier.offset(x = (-12).dp)) { open = !open }
        DetailReveal(open) { Text("$term. $text", Modifier.clip(RoundedCornerShape(12.dp)).background(c.panel2).padding(12.dp), style = MaterialTheme.typography.bodySmall, color = c.text) }
    }
}

/** The one "More detail" switch for the whole app (Detail.tsx), drawn as the spec's disclosure row. */
@Composable
fun MoreDetailButton(on: Boolean, what: String, onToggle: () -> Unit) = MoreDetailRow(on, what, Modifier.testTag("more-detail"), onToggle)
