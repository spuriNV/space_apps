package app.croplytics.ui.app

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import app.croplytics.data.repository.dataOrNull
import app.croplytics.ui.components.FilterPill
import app.croplytics.ui.components.focusRing
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import app.croplytics.data.repository.LoadState
import app.croplytics.domain.Timeline
import app.croplytics.ui.components.ErrorPanel
import app.croplytics.ui.components.FieldThumbnail
import app.croplytics.ui.components.OfflineNote
import app.croplytics.ui.components.Skeleton
import app.croplytics.ui.components.WakingPanel
import app.croplytics.ui.components.CoverStrip
import app.croplytics.ui.theme.CropLyticsTheme

/**
 * "Pick your field" (Options.tsx FieldPicker): one paper list, a row per field with a satellite thumbnail and outline, the
 * field's name, one line of facts, one line of what is notable and its 2023 to now season strips. BC is a quiet row at the end.
 */
@OptIn(ExperimentalLayoutApi::class)
fun LazyListScope.fieldPicker(state: MainUiState, onQuery: (String) -> Unit, onFamily: (String) -> Unit, onClear: () -> Unit, onSelect: (String) -> Unit, onBC: () -> Unit, onRetry: () -> Unit) {
    item(key = "pk-head") {
        val c = CropLyticsTheme.colors
        Column(Modifier.padding(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 4.dp).testTag("fields-panel")) {
            Text("Pick your field", style = MaterialTheme.typography.headlineSmall, color = c.text, modifier = Modifier.semantics { heading() })
        }
    }
    val total = (state.fields as? LoadState.Ready)?.data?.size ?: 0
    (state.fields as? LoadState.Ready)?.takeIf { it.offline }?.let { r -> item(key = "pk-offline") { app.croplytics.ui.components.Notice("Saved on ${app.croplytics.ui.components.savedOn(r.savedAt)}. Can't reach the server right now.") } }
    if (total > 1) item(key = "pk-filter") {
        val c = CropLyticsTheme.colors
        Column(Modifier.padding(horizontal = 16.dp)) {
            SearchPill(state.query, onQuery, "Search by town, county or crop", Modifier.testTag("pk-search"))
            Row(Modifier.horizontalScroll(rememberScrollState()).padding(vertical = 4.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                state.families.forEach { (f, n) ->
                    FilterPill(when (f) { "rice" -> "Rice"; "forage" -> "Forage"; else -> "British Columbia" }, state.family == f, Modifier.testTag("chip-$f"), count = n) { onFamily(f) }
                }
            }
        }
    }
    when (val f = state.fields) {
        LoadState.Waking -> item(key = "pk-waking") { WakingPanel() }
        is LoadState.Failed -> item(key = "pk-error") { ErrorPanel(f.error, onRetry) }
        LoadState.Loading -> items(4, key = { "pk-skel-$it" }) { RowSkeleton() }
        is LoadState.Ready -> {
            val shown = state.shown
            items(shown, key = { "pk-${it.id.id}" }) { row ->
                PickerRow(row, state.strips[row.id.id], row.id.id == state.selectedId) { onSelect(row.id.id) }
            }
            if (shown.isEmpty()) item(key = "pk-none") {
                val c = CropLyticsTheme.colors
                Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("No field matches. ", color = c.muted, style = MaterialTheme.typography.bodyMedium)
                    app.croplytics.ui.components.PillButton("Show all", app.croplytics.ui.components.PillKind.Outline, small = true, onClick = onClear)
                }
            }
        }
    }
    // the old "not set up yet" row only while the API serves no British Columbia field (App.tsx hasBC)
    if (state.fields.dataOrNull.orEmpty().none { it.id.region == "bc" }) item(key = "pk-bc") {
        val c = CropLyticsTheme.colors
        Row(Modifier.fillMaxWidth().clickable(onClick = onBC).padding(16.dp).testTag("pk-bc")) {
            Text("British Columbia: not set up yet. ", style = MaterialTheme.typography.bodySmall, color = c.muted)
            Text("See why", style = MaterialTheme.typography.bodySmall.copy(textDecoration = TextDecoration.Underline), color = c.accent)
        }
    }
}

@Composable
private fun PickerRow(row: FieldItem, strips: Map<Int, String>?, on: Boolean, onClick: () -> Unit) {
    val c = CropLyticsTheme.colors
    val id = row.id
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 1.dp).clip(RoundedCornerShape(12.dp)).background(if (on) c.accentContainer else androidx.compose.ui.graphics.Color.Transparent)
            .focusRing(RoundedCornerShape(12.dp)).clickable(role = Role.Button, onClickLabel = "Open field", onClick = onClick)
            .semantics { selected = on }.padding(12.dp).testTag("row-${id.id}"),
        verticalAlignment = Alignment.Top,
    ) {
        FieldThumbnail(row.rings, Modifier
            .then(if (on) Modifier.border(2.dp, c.accentOutline, RoundedCornerShape(10.dp)).padding(3.dp) else Modifier)
            .size(width = 88.dp, height = 60.dp).clip(RoundedCornerShape(8.dp)).semantics { contentDescription = "Satellite view of ${id.name}" })
        Spacer(Modifier.width(14.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(id.name, style = MaterialTheme.typography.titleMedium, color = c.text)
            Text("${id.place} · ${id.acres ?: "?"} acres · ${id.latestCrop?.lowercase() ?: "crop"} in ${id.latestCropYear ?: ""}", style = MaterialTheme.typography.bodySmall, color = c.text2)
            if (id.notable.isNotEmpty()) Text(id.notable, style = MaterialTheme.typography.labelSmall, color = c.muted)
            Spacer(Modifier.height(2.dp))
            val years = (Timeline.RECENT_FROM..(strips?.keys?.maxOrNull() ?: (Timeline.RECENT_FROM + 3))).toList()
            Row(Modifier.fillMaxWidth().clearAndSetSemantics { contentDescription = "Bare, green or flooded, ${years.first()} to ${years.last()}, from satellites" }, horizontalArrangement = Arrangement.spacedBy(3.dp)) {
                years.forEach { y ->
                    Column(Modifier.weight(1f)) {
                        CoverStrip(strips?.get(y) ?: "u".repeat(36), null, Modifier.clip(RoundedCornerShape(2.dp)), height = 7f)
                        Text("$y", style = MaterialTheme.typography.labelSmall, color = c.muted)
                    }
                }
            }
        }
    }
}

@Composable
private fun RowSkeleton() {
    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp)) {
        androidx.compose.foundation.layout.Box(Modifier.size(width = 96.dp, height = 72.dp)) { Skeleton(height = 72.dp) }
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Skeleton(height = 16.dp, widthFraction = 0.85f); Skeleton(height = 12.dp, widthFraction = 0.6f); Skeleton(height = 8.dp)
        }
    }
}
