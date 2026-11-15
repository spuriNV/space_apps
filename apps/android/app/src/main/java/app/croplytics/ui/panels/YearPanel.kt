package app.croplytics.ui.panels

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.croplytics.data.repository.LoadState
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.FieldNowLogic
import app.croplytics.domain.Timeline
import app.croplytics.domain.YearLogic
import app.croplytics.ui.app.FieldData
import app.croplytics.ui.app.MainUiState
import app.croplytics.ui.app.MoreDetailButton
import app.croplytics.ui.components.CoverKey
import app.croplytics.ui.components.CoverStrip
import app.croplytics.ui.components.MonthRow
import app.croplytics.ui.components.PageSkeleton
import app.croplytics.ui.theme.CropLyticsTheme

/** "This field's year" (YearSheet.tsx). */
@OptIn(ExperimentalLayoutApi::class)
fun LazyListScope.yearPanel(state: MainUiState, data: FieldData, a: PanelActions, onPlay: () -> Unit, onEarlier: () -> Unit) {
    val bundle = data.calendar.dataOrNull
    if (bundle == null) { item(key = "yr-wait") { PageSkeleton() }; return }
    val cal = bundle.calendar
    val view = YearLogic.build(data.item.loc, cal, data.daily.dataOrNull, bundle.ml, data.water.dataOrNull, data.stress.dataOrNull, state.t, state.showEarlier, state.detailOn)
    item(key = "yr-head") {
        val c = CropLyticsTheme.colors
        Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp).testTag("year-sheet"), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("This field’s year", style = MaterialTheme.typography.titleLarge, color = c.text, modifier = Modifier.semantics { heading() })
            Text(view.sentence, style = MaterialTheme.typography.bodyMedium, color = c.text2)
            Row(
                Modifier.border(1.dp, c.accent, RoundedCornerShape(3.dp)).clickable(role = Role.Button, onClick = onPlay).heightIn(min = 44.dp).padding(horizontal = 12.dp).testTag("play"),
                verticalAlignment = Alignment.CenterVertically,
            ) { Text(if (state.playing) "❚❚  Pause" else "▶  Replay on the map", style = MaterialTheme.typography.labelLarge, color = c.accent) }
            CoverKey(listOf('c' to YearLogic.LABEL.getValue('c'), 'p' to YearLogic.LABEL.getValue('p'), 'b' to YearLogic.LABEL.getValue('b'), 'w' to YearLogic.LABEL.getValue('w'), 'u' to "No clear view or not processed")) {
                Row(verticalAlignment = Alignment.CenterVertically) { Box(Modifier.size(8.dp).background(Color(0xFFA12A1C), CircleShape)); Text(" 1 inch of rain on bare ground", style = MaterialTheme.typography.labelSmall, color = c.muted) }
                Row(verticalAlignment = Alignment.CenterVertically) { Box(Modifier.size(width = 2.dp, height = 10.dp).background(c.mark)); Text(" on a crop or water", style = MaterialTheme.typography.labelSmall, color = c.muted) }
                if (state.detailOn && data.stress.dataOrNull?.weeks?.isNotEmpty() == true) Row(verticalAlignment = Alignment.CenterVertically) { Box(Modifier.size(8.dp).background(Color(0xFFE07A5F), CircleShape)); Text(" Crop-stress week", style = MaterialTheme.typography.labelSmall, color = c.muted) }
                if (state.detailOn && data.water.dataOrNull != null) Row(verticalAlignment = Alignment.CenterVertically) { Box(Modifier.size(width = 10.dp, height = 3.dp).background(Color(0xFF1F6FB8))); Text(" Standing water seen by NASA OPERA", style = MaterialTheme.typography.labelSmall, color = c.muted) }
            }
        }
    }
    item(key = "yr-grid") { YearGrid(view, state, bundle.ml != null, a.setT) }
    item(key = "yr-more") { MoreDetailButton(state.detailOn, "Machine learning, earlier years", a.toggleDetail) }
    item(key = "yr-foot") {
        val c = CropLyticsTheme.colors
        Column(Modifier.padding(horizontal = 16.dp, vertical = 4.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            val events = data.item.loc.events
            if (events.isNotEmpty()) FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                events.forEach { e -> TextButton(onClick = { a.setT(Timeline.dateToT(e.date)) }) { Text(e.short ?: e.title, color = c.accent) } }
            }
            if (state.detailOn) TextButton(onClick = onEarlier, modifier = Modifier.testTag("earlier")) {
                Text(if (state.showEarlier) "Show only the last 4 seasons" else "Show earlier years (2016–2022)", color = c.accent)
            }
            Text("${FieldNowLogic.calSource(cal)}, every 10 days, whole field. Rain from NASA GPM IMERG. Tap a square to move the map to that date.", style = MaterialTheme.typography.labelSmall, color = c.muted)
        }
    }
}

@Composable
private fun YearGrid(view: YearLogic.View, state: MainUiState, hasMl: Boolean, setT: (Int) -> Unit) {
    val c = CropLyticsTheme.colors
    var both by rememberSaveable { mutableStateOf(false) }
    val showBoth = both && state.detailOn
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (state.detailOn) {
            Row(Modifier.border(1.dp, c.line, RoundedCornerShape(3.dp)).testTag("ml-toggle")) {
                listOf(false to "Satellite rule", true to "Compare with machine learning").forEach { (v, label) ->
                    val on = both == v; val enabled = !v || hasMl
                    Text(label, Modifier.background(if (on) c.accent else c.paper).clickable(enabled = enabled) { both = v }.padding(horizontal = 10.dp, vertical = 8.dp),
                        style = MaterialTheme.typography.labelMedium, color = if (on) c.onAccent else if (enabled) c.text else c.muted)
                }
            }
            if (showBoth) Text("Machine learning: ${view.verdict.short.lowercase()}. ${view.verdict.long}", Modifier.testTag("ml-note"),
                style = MaterialTheme.typography.bodySmall, color = if (view.verdict.short == "Below accuracy target") c.warn else c.text2)
        }
        Row { Spacer(Modifier.width(0.dp)); MonthRow() }
        // typical year
        Column(Modifier.background(c.panel2).padding(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Typical year", style = MaterialTheme.typography.labelLarge, color = c.text); Spacer(Modifier.width(6.dp))
                Text(view.typicalLabel, Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, color = c.muted)
                Text("${view.typicalBare} bare days", style = MaterialTheme.typography.labelSmall, color = c.text2)
            }
            CoverStrip(view.typical, null, height = 14f)
        }
        view.rows.forEach { r ->
            Column(
                Modifier.fillMaxWidth().then(if (r.current) Modifier.border(1.dp, c.accent, RoundedCornerShape(2.dp)) else Modifier).padding(4.dp)
                    .clearAndSetSemantics { contentDescription = "${r.year}, ${r.crop}: bare ${r.bareDays} days; 1-inch rain days on bare ground ${r.rainOnBare}" },
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("${r.year}", style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.SemiBold), color = c.text); Spacer(Modifier.width(6.dp))
                    Text(r.crop + if (showBoth && !r.empty) " · rule / machine learning" else "", Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, color = c.muted)
                    Text("bare ${r.bareDays} · rain on bare ${r.rainOnBare}", style = MaterialTheme.typography.labelSmall, color = c.text2)
                }
                CoverStrip(r.rule, if (r.current) Timeline.stepOf(state.t) else null, height = 16f, marks = r.marks) { step -> setT(Timeline.tOf(r.year, step)) }
                if (showBoth) CoverStrip(r.ml, null, Modifier.padding(top = 2.dp), height = 10f)
            }
        }
        Row { Text("Bare days a year, and 1-inch rain days that landed on bare ground.", style = MaterialTheme.typography.labelSmall, color = c.muted) }
    }
}
