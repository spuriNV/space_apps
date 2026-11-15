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
import androidx.compose.foundation.layout.offset
import androidx.compose.animation.animateContentSize
import app.croplytics.domain.Fmt
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.filled.Print
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.unit.sp
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

/**
 * Field header (spec 4.10): paper, the field's name with a close disc, facts and id. It collapses to one line once the content
 * scrolls ([stuck]); at half and full height a row of next-step pills follows, the primary first.
 */
@Composable
fun FieldHeaderBar(data: FieldData, stuck: Boolean, showActions: Boolean, onClose: () -> Unit, openTab: (app.croplytics.ui.app.Tab) -> Unit) {
    val c = CropLyticsTheme.colors
    val id = data.item.id
    val title by androidx.compose.animation.core.animateFloatAsState(if (stuck) 20f else 22f, app.croplytics.ui.components.motion(240), label = "title")
    Column(
        Modifier.fillMaxWidth().background(c.paper).then(if (stuck) Modifier.shadow(3.dp) .background(c.paper) else Modifier)
            .padding(start = 16.dp, end = 8.dp, top = if (stuck) 4.dp else 8.dp, bottom = 8.dp).testTag("field-panel"),
    ) {
        Row(verticalAlignment = Alignment.Top) {
            Text(id.name, Modifier.weight(1f).padding(top = 6.dp).semantics { heading() }, style = MaterialTheme.typography.titleLarge.copy(fontSize = title.sp, lineHeight = (title + 4).sp),
                color = c.text, maxLines = if (stuck) 1 else 3, overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis)
            app.croplytics.ui.components.IconDisc("Close", onClick = onClose)
        }
        Text(
            androidx.compose.ui.text.buildAnnotatedString {
                pushStyle(androidx.compose.ui.text.SpanStyle(fontWeight = FontWeight.Bold, color = c.text)); append("${id.acres ?: "?"} acres"); pop()
                append(", ${id.latestCrop?.lowercase() ?: "crop"} in ${id.latestCropYear ?: ""}, ${id.place}")
            },
            style = if (stuck) MaterialTheme.typography.bodySmall else MaterialTheme.typography.bodyMedium, color = c.text2, maxLines = if (stuck) 1 else 2,
        )
        androidx.compose.animation.AnimatedVisibility(!stuck) { Text(id.idLine, style = MaterialTheme.typography.labelSmall, color = c.muted) }
        if (showActions) Row(Modifier.padding(top = 10.dp).horizontalScroll(rememberScrollState()).testTag("sheet-actions"), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            app.croplytics.ui.components.PillButton("Print for your adviser", app.croplytics.ui.components.PillKind.Primary, icon = androidx.compose.material.icons.Icons.Filled.Print, small = true, modifier = Modifier.testTag("step-Print")) { openTab(app.croplytics.ui.app.Tab.Print) }
            listOf("What’s likely this winter" to app.croplytics.ui.app.Tab.Season, "This field’s year" to app.croplytics.ui.app.Tab.Year, "Compare rotations" to app.croplytics.ui.app.Tab.Compare).forEach { (l, t) ->
                app.croplytics.ui.components.PillButton(l, app.croplytics.ui.components.PillKind.Tonal, small = true, modifier = Modifier.testTag("step-${t.name}")) { openTab(t) }
            }
        }
    }
}

/** "Your field now" (Options.tsx FieldPanel + FieldNow.tsx). */
@OptIn(ExperimentalLayoutApi::class)
fun LazyListScope.fieldNowPanel(state: MainUiState, data: FieldData, view: FieldNowView, nasa: List<NasaDataset>, glossary: Map<String, Pair<String, String>>, a: PanelActions) {
    val detail = state.detailOn
    item(key = "fn-title") {
        app.croplytics.ui.components.SectionHead(if (state.isToday) "Your field now" else "Your field in ${Timeline.when_(state.t)}", Modifier.padding(top = 0.dp),
            action = if (state.isToday) null else "Back to today" to a.backToToday)
    }
    item(key = "fn-glance") { GlanceBox(data, view) }
    view.answers.filter { detail || !it.moreOnly }.forEachIndexed { i, ans ->
        item(key = "fn-ans-${ans.question}") {
            if (i > 0) HorizontalDivider(Modifier.padding(horizontal = 16.dp), color = CropLyticsTheme.colors.lineSoft)
            AnswerView(ans, detail, glossary)
        }
    }
    if (data.item.loc.isBC) item(key = "fn-first-nations") { FirstNationsSection(data, detail) }
    item(key = "fn-nation") { NationToolsSection(data.item.loc.id, data.item.loc.isBC) }
    item(key = "fn-more") { MoreDetailButton(detail, "Sources, past seasons, 3D", a.toggleDetail) }
    if (detail) {
        if (data.item.loc.isBC) item(key = "fn-salmon") { SalmonCard(data.item.loc.id) }
        item(key = "fn-nasa") { Box(Modifier.animateItem()) { NasaSection(data, nasa) } }
        item(key = "fn-about") {
            val c = CropLyticsTheme.colors
            Column(Modifier.animateItem()) {
                app.croplytics.ui.components.SectionHead("About the ground", action = "Look in 3D" to a.drill, helper = "Under the field in 3D: crop, soil moisture, groundwater.")
            }
            Column(Modifier.padding(horizontal = 16.dp)) {
                FieldNowLogic.aboutField(data.item.loc, data.calendar.dataOrNull?.calendar, data.insurance.dataOrNull?.summary(), data.insurance.dataOrNull).forEach { (k, v) ->
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
                app.croplytics.ui.components.SectionHead("The last 3 seasons", Modifier.animateItem())
                Column(Modifier.padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    FieldNowLogic.lastSeasons(data.item.loc, cal).forEach { s ->
                        Column {
                            Row { Text("${s.year}", Modifier.width(44.dp), style = MaterialTheme.typography.labelLarge, color = c.text); Text(s.text, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = c.text2) }
                            CoverStrip(s.strip, null, Modifier.padding(start = 44.dp).clip(RoundedCornerShape(4.dp)), height = 8f)
                        }
                    }
                }
            }
        }
        if (data.item.loc.events.isNotEmpty()) item(key = "fn-events") {
            val c = CropLyticsTheme.colors
            app.croplytics.ui.components.SectionHead("What happened around here", Modifier.animateItem(), helper = "Tap one to move the map to that date.")
            Column(Modifier.padding(horizontal = 8.dp)) {
                data.item.loc.events.forEach { e ->
                    Column(Modifier.fillMaxWidth().heightIn(min = 48.dp).clip(RoundedCornerShape(8.dp)).clickable { a.setT(Timeline.dateToT(e.date)) }.padding(horizontal = 8.dp, vertical = 8.dp)) {
                        Text(Timeline.fmtDate(e.date), style = MaterialTheme.typography.labelSmall, color = c.muted)
                        Text(e.title, style = MaterialTheme.typography.bodyMedium, color = c.text)
                        e.detail?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = c.text2) }
                    }
                }
            }
        }
        item(key = "fn-sources") {
            app.croplytics.ui.components.PillButton("Sources", app.croplytics.ui.components.PillKind.Text, modifier = Modifier.padding(start = 16.dp, top = 12.dp).testTag("sources-link"), onClick = a.openSources)
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
        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp).shadow(1.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp)).background(c.raised)
            .border(1.dp, c.lineSoft, RoundedCornerShape(12.dp)).padding(12.dp).testTag("glance"),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(verticalAlignment = Alignment.Top) {
            FieldThumbnail(data.item.rings, Modifier.size(width = 96.dp, height = 64.dp).clip(RoundedCornerShape(8.dp)))
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text("${g.year} so far", style = MaterialTheme.typography.labelSmall, color = c.muted)
                CoverStrip(g.strip, g.todayStep, Modifier.clip(RoundedCornerShape(4.dp)), height = 12f)
                MonthTicks()
                if (g.state != null) Text(g.state, style = MaterialTheme.typography.titleMedium, color = c.text) else Skeleton(height = 14.dp, widthFraction = 0.6f)
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
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(ans.question, style = MaterialTheme.typography.bodySmall, color = c.muted)
        if (!ans.ready) { Skeleton(height = 16.dp, widthFraction = 0.7f); return@Column }
        if (ans.headline.isNotEmpty()) Row(verticalAlignment = Alignment.CenterVertically) {
            ans.swatch?.let { Box(Modifier.size(11.dp).background(clsColor(it))); Spacer(Modifier.width(6.dp)) }
            Text(ans.headline, style = MaterialTheme.typography.titleMedium, color = if (ans.warn) c.warn else c.text)
        }
        ans.soilMix?.let { SoilBar(it) }
        if (ans.detail.isNotEmpty()) Text(ans.detail, style = MaterialTheme.typography.bodyMedium, color = c.text2)
        if (detail && ans.moreDetail.isNotEmpty()) Text(ans.moreDetail, style = MaterialTheme.typography.bodyMedium, color = c.text2)
        ans.extra?.let { Text(it, style = MaterialTheme.typography.bodySmall.copy(fontStyle = FontStyle.Italic), color = c.text2) }
        if (ans.cite.isNotEmpty()) Text(ans.cite, style = MaterialTheme.typography.labelSmall, color = c.muted)
        ans.gloss?.let { What(it, glossary) }
    }
}

/** "NASA data behind this field": the ISS photo and every NASA dataset, what it tells you, how coarse, whether it is live. */
@Composable
private fun NasaSection(data: FieldData, list: List<NasaDataset>) {
    val c = CropLyticsTheme.colors
    val uri = LocalUriHandler.current
    var open by rememberSaveable { mutableStateOf(false) }
    Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp).testTag("nasa-section"), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text("NASA data behind this field", style = MaterialTheme.typography.titleLarge, color = c.text, modifier = Modifier.padding(top = 16.dp).semantics { heading() })
        data.iss.dataOrNull?.let { p ->
            val ym = p.date.split("-").mapNotNull { it.toIntOrNull() }
            val month = if (ym.size >= 2) "${Timeline.MONTHS_FULL[ym[1] - 1]} ${ym[0]}" else p.date
            Column(Modifier.testTag("iss-photo")) {
                AsyncImage(p.url, "Astronaut photo taken from the International Space Station, $month: ${p.features.lowercase()}",
                    Modifier.fillMaxWidth().aspectRatio(1.5f).clip(RoundedCornerShape(12.dp)).clickable { runCatching { uri.openUri(p.pageUrl) } }, contentScale = ContentScale.Crop)
                Text("Seen from the ISS near your field, $month", style = MaterialTheme.typography.labelLarge, color = c.text)
                Text("Centre of the photo about ${maxOf(1, Math.round(p.miles).toInt())} miles from the field. " +
                    p.features.split(",").map { it.trim().lowercase() }.filter { it != "agriculture" }.take(3).joinToString(", ") { w -> w.split(" ").joinToString(" ") { it.replaceFirstChar(Char::uppercase) } } + ".",
                    style = MaterialTheme.typography.bodySmall, color = c.text2)
                Text("${p.credit}. Photo ${p.photoId}, eol.jsc.nasa.gov.", style = MaterialTheme.typography.labelSmall, color = c.muted)
            }
        }
        val live = list.count { it.status == NasaStatus.Live }
        app.croplytics.ui.components.MoreDetailRow(open, "What each tells you, how coarse, whether it is live", Modifier.testTag("nasa-toggle").padding(horizontal = 0.dp)) { open = !open }
        Text("All ${list.size} NASA datasets: $live live on this screen", style = MaterialTheme.typography.bodySmall, color = c.muted)
        if (open) list.forEach { d ->
            Column(Modifier.padding(vertical = 4.dp)) {
                Text(d.name, style = MaterialTheme.typography.labelLarge, color = c.text)
                Text(d.tells, style = MaterialTheme.typography.bodySmall, color = c.text2)
                Text("${d.scale}. ${d.agency}. ${d.status.words}", style = MaterialTheme.typography.labelSmall, color = if (d.status == NasaStatus.Example) c.warn else c.muted)
            }
        }
    }
}

/** "Working with First Nations" (FirstNations.tsx, BC fields only): the statement and two plain lines; the rest under More detail. */
@Composable
private fun FirstNationsSection(data: FieldData, detail: Boolean) {
    val c = CropLyticsTheme.colors
    val uri = LocalUriHandler.current
    val s = data.item.loc.firstNations
    val fn = data.firstNations.dataOrNull
    if (s == null && fn == null) return
    val onReserve = fn?.fieldOnReserve ?: s!!.fieldOnReserve
    val km = fn?.nearestKm ?: s?.nearestKm; val nation = fn?.nearestNation ?: s?.nearestNation
    val lower = fn?.lowerRiverNation?.nation ?: (s?.lowerRiverNation as? kotlinx.serialization.json.JsonPrimitive)?.content
    val river = data.item.loc.waterContext?.watershed?.split('(', ';', ',')?.first()?.trim()?.ifBlank { null } ?: "river"
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp).testTag("first-nations"), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text("Working with First Nations", Modifier.padding(top = 20.dp).semantics { heading() }, style = MaterialTheme.typography.titleLarge, color = c.text)
        Text(fn?.statement ?: s!!.statement, style = MaterialTheme.typography.bodyMedium, color = c.text)
        Text(if (onReserve) "This field is on reserve land." else "This field is not on reserve land; nearest reserve ${km?.let { Fmt.one(it) } ?: "?"} km ($nation).", style = MaterialTheme.typography.bodyMedium, color = c.text2)
        lower?.let { Text("Nation on the lower $river: $it.", style = MaterialTheme.typography.bodyMedium, color = c.text2) }
        fn?.lowerRiverNation?.url?.let { u -> app.croplytics.ui.components.PillButton("${fn.lowerRiverNation.nation} lands page", app.croplytics.ui.components.PillKind.Text, small = true, modifier = Modifier.offset(x = (-12).dp)) { runCatching { uri.openUri(u) } } }
        if (detail) Column(Modifier.animateContentSize().testTag("first-nations-detail"), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            if (fn == null) { Text(if (data.firstNations is app.croplytics.data.repository.LoadState.Failed) "More on the Nations is not available right now." else "Loading…", style = MaterialTheme.typography.bodySmall, color = c.muted); return@Column }
            val near = fn.nearby.filter { it.distanceKm <= 20 }.sortedBy { it.distanceKm }; val rest = fn.nearby.filter { it.distanceKm > 20 }
            Text("Reserves near this field", Modifier.padding(top = 8.dp), style = MaterialTheme.typography.titleSmall, color = c.text)
            near.forEach { r -> Row { Text("${Fmt.one(r.distanceKm)} km", Modifier.width(64.dp), style = MaterialTheme.typography.labelLarge, color = c.text); Column { Text(app.croplytics.domain.BcLogic.reserveName(r.reserve), style = MaterialTheme.typography.bodySmall, color = c.text); Text(r.nation, style = MaterialTheme.typography.labelSmall, color = c.muted) } } }
            if (rest.isNotEmpty()) Text("${rest.size} more within ${kotlin.math.ceil(rest.maxOf { it.distanceKm }).toInt()} km: ${rest.map { it.nation }.distinct().joinToString(", ")}.", style = MaterialTheme.typography.bodySmall, color = c.text2)
            fn.notes.firstOrNull()?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = c.text2) }
            Text("How we would start", Modifier.padding(top = 8.dp), style = MaterialTheme.typography.titleSmall, color = c.text)
            fn.engagementSteps.forEachIndexed { i, x -> Text("${i + 1}. $x", style = MaterialTheme.typography.bodySmall, color = c.text2) }
            Text("Principles we follow", Modifier.padding(top = 8.dp), style = MaterialTheme.typography.titleSmall, color = c.text)
            fn.principles.forEach { p -> Column { Text(p.name, Modifier.then(if (p.url != null) Modifier.clickable { runCatching { uri.openUri(p.url) } } else Modifier), style = MaterialTheme.typography.labelLarge, color = if (p.url != null) c.accent else c.text); Text(p.description, style = MaterialTheme.typography.bodySmall, color = c.text2) } }
            Text("Public contact pages", Modifier.padding(top = 8.dp), style = MaterialTheme.typography.titleSmall, color = c.text)
            fn.contacts.forEach { x -> Column { Text(x.nation, Modifier.then(if (x.url != null) Modifier.clickable { runCatching { uri.openUri(x.url) } } else Modifier), style = MaterialTheme.typography.labelLarge, color = if (x.url != null) c.accent else c.text); Text(x.department, style = MaterialTheme.typography.bodySmall, color = c.text2) } }
            if (fn.waterTimeline.isNotEmpty()) {
                Text("Water and salmon, ${fn.waterTimeline.first().date.take(4)}–${fn.waterTimeline.last().date.take(4)}", Modifier.padding(top = 8.dp), style = MaterialTheme.typography.titleSmall, color = c.text)
                fn.waterTimeline.forEach { x -> Row { Text(if (x.date.length == 10) Timeline.fmtDate(x.date) else x.date, Modifier.width(96.dp), style = MaterialTheme.typography.labelSmall, color = c.muted); Text(x.title, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = c.text2) } }
            }
            Text("${fn.source?.title ?: "BC Data Catalogue"}${fn.notes.getOrNull(1)?.let { ". $it" } ?: ""}", style = MaterialTheme.typography.labelSmall, color = c.muted)
        }
    }
}
