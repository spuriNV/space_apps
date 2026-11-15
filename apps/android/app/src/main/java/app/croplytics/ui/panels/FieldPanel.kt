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
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.HorizontalDivider
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.Answer
import app.croplytics.domain.FieldNowView
import app.croplytics.domain.FieldNowLogic
import app.croplytics.domain.NasaDataset
import app.croplytics.domain.NasaStatus
import app.croplytics.domain.Timeline
import app.croplytics.domain.summary
import app.croplytics.ui.app.FieldData
import app.croplytics.ui.app.MainUiState
import app.croplytics.ui.app.MoreDetailButton
import app.croplytics.ui.app.What
import app.croplytics.ui.components.CoverStrip
import app.croplytics.ui.components.FieldThumbnail
import app.croplytics.ui.components.MeterView
import app.croplytics.ui.components.MonthTicks
import app.croplytics.ui.components.PercentileTrack
import app.croplytics.ui.components.Skeleton
import app.croplytics.ui.components.SoilBar
import app.croplytics.ui.components.clsColor
import app.croplytics.ui.theme.CropLyticsTheme
import coil3.compose.AsyncImage

/** Callbacks a field panel can raise. */
data class PanelActions(
    val setT: (Int) -> Unit,
    val backToToday: () -> Unit,
    val toggleDetail: () -> Unit,
    val drill: () -> Unit,
    val openSources: () -> Unit,
    val openTab: (app.croplytics.ui.app.Tab) -> Unit,
    val close: () -> Unit,
)

/** Field header (Options.tsx fp-head): the field's name, facts and state field number. */
fun LazyListScope.fieldHeader(data: FieldData, onClose: () -> Unit) {
    item(key = "fp-head") {
        val c = CropLyticsTheme.colors
        val id = data.item.id
        Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 4.dp).testTag("field-panel")) {
            Row(verticalAlignment = Alignment.Top) {
                Text(id.name, Modifier.weight(1f).semantics { heading() }, style = MaterialTheme.typography.headlineSmall, color = c.text)
                TextButton(onClick = onClose) { Text("Close", color = c.accent) }
            }
            Text(
                "${id.acres ?: "?"} acres, ${id.latestCrop?.lowercase() ?: "crop"} in ${id.latestCropYear ?: ""}, ${id.place}",
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold), color = c.text,
            )
            Text(id.idLine, style = MaterialTheme.typography.labelSmall, color = c.muted)
        }
    }
}

/** "Your field now" (Options.tsx FieldPanel + FieldNow.tsx). */
@OptIn(ExperimentalLayoutApi::class)
fun LazyListScope.fieldNowPanel(state: MainUiState, data: FieldData, view: FieldNowView, nasa: List<NasaDataset>, glossary: Map<String, Pair<String, String>>, a: PanelActions) {
    val detail = state.detailOn
    item(key = "fn-title") {
        val c = CropLyticsTheme.colors
        Row(Modifier.fillMaxWidth().padding(start = 16.dp, end = 8.dp, top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(if (state.isToday) "Your field now" else "Your field in ${Timeline.when_(state.t)}", Modifier.weight(1f).semantics { heading() }, style = MaterialTheme.typography.titleMedium, color = c.text)
            if (!state.isToday) TextButton(onClick = a.backToToday) { Text("Back to today", color = c.accent) }
        }
    }
    item(key = "fn-glance") { GlanceBox(data, view) }
    view.answers.filter { detail || !it.moreOnly }.forEachIndexed { i, ans ->
        item(key = "fn-ans-${ans.question}") {
            if (i > 0) HorizontalDivider(Modifier.padding(horizontal = 16.dp), color = CropLyticsTheme.colors.lineSoft)
            AnswerView(ans, detail, glossary)
        }
    }
    item(key = "fn-actions") { Actions(a.openTab) }
    item(key = "fn-more") { MoreDetailButton(detail, "Sources, past seasons, 3D", a.toggleDetail) }
    if (detail) {
        item(key = "fn-nasa") { NasaSection(data, nasa) }
        item(key = "fn-about") {
            val c = CropLyticsTheme.colors
            Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                Text("About the ground", style = MaterialTheme.typography.titleMedium, color = c.text, modifier = Modifier.semantics { heading() })
                Text(
                    "Look under the field in 3D: crop, soil moisture, groundwater", Modifier.clickable(role = Role.Button, onClick = a.drill).padding(vertical = 6.dp).testTag("step-drill"),
                    style = MaterialTheme.typography.bodySmall.copy(textDecoration = TextDecoration.Underline), color = c.accent,
                )
                FieldNowLogic.aboutField(data.item.loc, data.calendar.dataOrNull?.calendar, data.insurance.dataOrNull?.summary()).forEach { (k, v) ->
                    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp)) {
                        Text(k, Modifier.width(100.dp), style = MaterialTheme.typography.bodySmall, color = c.muted)
                        Text(v, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = if (k == "Salt" && v.startsWith("Salty")) c.warn else c.text)
                    }
                }
            }
        }
        data.calendar.dataOrNull?.calendar?.let { cal ->
            item(key = "fn-seasons") {
                val c = CropLyticsTheme.colors
                Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("The last 3 seasons", style = MaterialTheme.typography.titleMedium, color = c.text, modifier = Modifier.semantics { heading() })
                    FieldNowLogic.lastSeasons(data.item.loc, cal).forEach { s ->
                        Column {
                            Row { Text("${s.year}", Modifier.width(44.dp), style = MaterialTheme.typography.labelLarge, color = c.text); Text(s.text, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = c.text2) }
                            CoverStrip(s.strip, null, Modifier.padding(start = 44.dp), height = 8f)
                        }
                    }
                }
            }
        }
        if (data.item.loc.events.isNotEmpty()) item(key = "fn-events") {
            val c = CropLyticsTheme.colors
            Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                Text("What happened around here", style = MaterialTheme.typography.titleMedium, color = c.text, modifier = Modifier.semantics { heading() })
                Text("Tap one to move the map to that date.", style = MaterialTheme.typography.labelSmall, color = c.muted)
                data.item.loc.events.forEach { e ->
                    Column(Modifier.fillMaxWidth().clickable { a.setT(Timeline.dateToT(e.date)) }.padding(vertical = 6.dp)) {
                        Text(Timeline.fmtDate(e.date), style = MaterialTheme.typography.labelSmall, color = c.muted)
                        Text(e.title, style = MaterialTheme.typography.bodyMedium, color = c.text)
                        e.detail?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = c.text2) }
                    }
                }
            }
        }
        item(key = "fn-sources") {
            Text("Sources", Modifier.clickable(role = Role.Button, onClick = a.openSources).padding(16.dp).testTag("sources-link"),
                style = MaterialTheme.typography.labelLarge.copy(textDecoration = TextDecoration.Underline), color = CropLyticsTheme.colors.accent)
        }
    }
    item(key = "fn-foot") {
        Text("CropLytics helps the grower and adviser decide; it does not replace either.", Modifier.padding(16.dp), style = MaterialTheme.typography.bodySmall, color = CropLyticsTheme.colors.muted)
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun GlanceBox(data: FieldData, view: FieldNowView) {
    val c = CropLyticsTheme.colors
    val g = view.glance
    Column(
        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp).border(1.dp, c.line, RoundedCornerShape(3.dp)).padding(12.dp).testTag("glance"),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(verticalAlignment = Alignment.Top) {
            FieldThumbnail(data.item.rings, Modifier.size(width = 96.dp, height = 64.dp).clip(RoundedCornerShape(2.dp)))
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text("${g.year} so far", style = MaterialTheme.typography.labelSmall, color = c.muted)
                CoverStrip(g.strip, g.todayStep, height = 12f)
                MonthTicks()
                if (g.state != null) Text(g.state, style = MaterialTheme.typography.titleSmall, color = c.text) else Skeleton(height = 14.dp, widthFraction = 0.6f)
            }
        }
        FlowRow(horizontalArrangement = Arrangement.spacedBy(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp), maxItemsInEachRow = 2) {
            val cell = Modifier.weight(1f).widthIn(min = 130.dp)
            val loading = data.daily is app.croplytics.data.repository.LoadState.Loading || data.daily is app.croplytics.data.repository.LoadState.Waking
            MeterView(g.rain, cell, unavailable = !loading && g.rain.value == null && data.nasaNow !is app.croplytics.data.repository.LoadState.Loading)
            MeterView(g.need, cell, unavailable = data.strategies is app.croplytics.data.repository.LoadState.Failed)
            MeterView(g.green, cell, unavailable = data.calendar is app.croplytics.data.repository.LoadState.Failed)
            PercentileTrack(g.soilPct, g.gwPct, g.soilNote, g.regionalReady, cell)
        }
    }
}

/** One answer (FieldNow.tsx .ans): question, plain answer, numbers in a sentence, one source line, "What's this?". */
@Composable
fun AnswerView(ans: Answer, detail: Boolean, glossary: Map<String, Pair<String, String>>) {
    val c = CropLyticsTheme.colors
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(ans.question, style = MaterialTheme.typography.bodySmall, color = c.muted)
        if (!ans.ready) { Skeleton(height = 16.dp, widthFraction = 0.7f); return@Column }
        if (ans.headline.isNotEmpty()) Row(verticalAlignment = Alignment.CenterVertically) {
            ans.swatch?.let { Box(Modifier.size(11.dp).background(clsColor(it))); Spacer(Modifier.width(6.dp)) }
            Text(ans.headline, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold), color = if (ans.warn) c.warn else c.text)
        }
        ans.soilMix?.let { SoilBar(it) }
        if (ans.detail.isNotEmpty()) Text(ans.detail, style = MaterialTheme.typography.bodyMedium, color = c.text2)
        if (detail && ans.moreDetail.isNotEmpty()) Text(ans.moreDetail, style = MaterialTheme.typography.bodyMedium, color = c.text2)
        ans.extra?.let { Text(it, style = MaterialTheme.typography.bodySmall.copy(fontStyle = FontStyle.Italic), color = c.text2) }
        if (ans.cite.isNotEmpty()) Text(ans.cite, style = MaterialTheme.typography.labelSmall, color = c.muted)
        ans.gloss?.let { What(it, glossary) }
    }
}

/** The next steps (shared.tsx Actions), the adviser summary as the primary one. */
@Composable
private fun Actions(openTab: (app.croplytics.ui.app.Tab) -> Unit) {
    val c = CropLyticsTheme.colors
    val actions = listOf(
        Triple("What’s likely this winter", app.croplytics.ui.app.Tab.Season, false), Triple("This field’s year", app.croplytics.ui.app.Tab.Year, false),
        Triple("Compare rotations", app.croplytics.ui.app.Tab.Compare, false), Triple("Print for your adviser", app.croplytics.ui.app.Tab.Print, true),
    )
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        actions.chunked(2).forEach { pair ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                pair.forEach { (label, tab, primary) ->
                    Box(
                        Modifier.weight(1f).heightIn(min = 52.dp)
                            .then(if (primary) Modifier.background(c.accent, RoundedCornerShape(3.dp)) else Modifier.border(1.dp, c.line, RoundedCornerShape(3.dp)))
                            .clickable(role = Role.Button) { openTab(tab) }.padding(12.dp).testTag("step-${tab.name}"),
                        contentAlignment = Alignment.CenterStart,
                    ) { Text(label, style = MaterialTheme.typography.labelLarge, color = if (primary) c.onAccent else c.text) }
                }
            }
        }
    }
}

/** "NASA data behind this field": the ISS photo and every NASA dataset, what it tells you, how coarse, whether it is live. */
@Composable
private fun NasaSection(data: FieldData, list: List<NasaDataset>) {
    val c = CropLyticsTheme.colors
    val uri = LocalUriHandler.current
    var open by rememberSaveable { mutableStateOf(false) }
    Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp).testTag("nasa-section"), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text("NASA data behind this field", style = MaterialTheme.typography.titleMedium, color = c.text, modifier = Modifier.semantics { heading() })
        data.iss.dataOrNull?.let { p ->
            val ym = p.date.split("-").mapNotNull { it.toIntOrNull() }
            val month = if (ym.size >= 2) "${Timeline.MONTHS_FULL[ym[1] - 1]} ${ym[0]}" else p.date
            Column(Modifier.testTag("iss-photo")) {
                AsyncImage(p.url, "Astronaut photo taken from the International Space Station, $month: ${p.features.lowercase()}",
                    Modifier.fillMaxWidth().aspectRatio(1.5f).clip(RoundedCornerShape(2.dp)).clickable { runCatching { uri.openUri(p.pageUrl) } }, contentScale = ContentScale.Crop)
                Text("Seen from the ISS near your field, $month", style = MaterialTheme.typography.labelLarge, color = c.text)
                Text("Centre of the photo about ${maxOf(1, Math.round(p.miles).toInt())} miles from the field. " +
                    p.features.split(",").map { it.trim().lowercase() }.filter { it != "agriculture" }.take(3).joinToString(", ") { w -> w.split(" ").joinToString(" ") { it.replaceFirstChar(Char::uppercase) } } + ".",
                    style = MaterialTheme.typography.bodySmall, color = c.text2)
                Text("${p.credit}. Photo ${p.photoId}, eol.jsc.nasa.gov.", style = MaterialTheme.typography.labelSmall, color = c.muted)
            }
        }
        val live = list.count { it.status == NasaStatus.Live }
        Text(
            "All ${list.size} NASA datasets: $live live on this screen", Modifier.clickable(role = Role.Button) { open = !open }.heightIn(min = 40.dp).padding(vertical = 8.dp).testTag("nasa-toggle"),
            style = MaterialTheme.typography.labelLarge.copy(textDecoration = TextDecoration.Underline), color = c.accent,
        )
        if (open) list.forEach { d ->
            Column(Modifier.padding(vertical = 4.dp)) {
                Text(d.name, style = MaterialTheme.typography.labelLarge, color = c.text)
                Text(d.tells, style = MaterialTheme.typography.bodySmall, color = c.text2)
                Text("${d.scale}. ${d.agency}. ${d.status.words}", style = MaterialTheme.typography.labelSmall, color = if (d.status == NasaStatus.Example) c.warn else c.muted)
            }
        }
    }
}
