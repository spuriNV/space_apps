package app.croplytics.ui.now

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Place
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.croplytics.data.remote.dto.GlossaryItemDto
import app.croplytics.domain.Fmt
import app.croplytics.ui.common.DetailPart
import app.croplytics.ui.common.glossaryLookup
import app.croplytics.ui.components.ActionRow
import app.croplytics.ui.components.AnswerBlock
import app.croplytics.ui.components.BodyText
import app.croplytics.ui.components.Cite
import app.croplytics.ui.components.CoverKey
import app.croplytics.ui.components.DetailUnavailable
import app.croplytics.ui.components.ErrorPanel
import app.croplytics.ui.components.FieldMap
import app.croplytics.ui.components.LabelValue
import app.croplytics.ui.components.Meter
import app.croplytics.ui.components.MonthTicks
import app.croplytics.ui.components.MoreDetail
import app.croplytics.ui.components.OfflineNote
import app.croplytics.ui.components.PageSkeleton
import app.croplytics.ui.components.PercentileTrack
import app.croplytics.ui.components.SeasonStripBar
import app.croplytics.ui.components.SectionHeading
import app.croplytics.ui.components.Skeleton
import app.croplytics.ui.components.WakingPanel
import app.croplytics.ui.field.FieldTab
import app.croplytics.ui.theme.CropLyticsTheme
import app.croplytics.ui.theme.DataColors

@Composable
fun FieldNowScreen(onOpenMap: () -> Unit, onGoTo: (FieldTab) -> Unit, viewModel: FieldNowViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    FieldNowContent(state, onRetry = viewModel::retry, onOpenMap = onOpenMap, onGoTo = onGoTo)
}

@OptIn(ExperimentalLayoutApi::class, ExperimentalMaterial3Api::class)
@Composable
fun FieldNowContent(
    state: FieldNowUiState,
    onRetry: () -> Unit,
    onOpenMap: () -> Unit,
    onGoTo: (FieldTab) -> Unit,
    showMap: Boolean = true,
) {
    val c = CropLyticsTheme.colors
    var glossaryOpen by remember { mutableStateOf<GlossaryItemDto?>(null) }
    when {
        state.identity == null && state.waking -> { WakingPanel(); return }
        state.identity == null && state.error != null -> { ErrorPanel(state.error, onRetry); return }
        state.identity == null || state.summary == null -> { PageSkeleton(); return }
    }
    val summary = state.summary!!
    PullToRefreshBox(isRefreshing = false, onRefresh = onRetry, modifier = Modifier.fillMaxSize()) {
        LazyColumn(Modifier.fillMaxSize().testTag("field-now"), contentPadding = app.croplytics.ui.components.pageContentPadding()) {
            state.offlineSavedAt?.let { item { OfflineNote(it) } }
            if (state.waking) item { WakingPanel() }
            if (showMap && state.rings.isNotEmpty()) item {
                Box(Modifier.fillMaxWidth().height(190.dp)) {
                    FieldMap(state.rings, interactive = false, modifier = Modifier.fillMaxSize().clearAndSetSemantics { contentDescription = "Satellite view of the field with its outline" })
                    Surface(
                        onClick = onOpenMap,
                        modifier = Modifier.align(Alignment.TopEnd).padding(10.dp),
                        shape = RoundedCornerShape(2.dp),
                        color = c.paper,
                        border = androidx.compose.foundation.BorderStroke(1.dp, c.text),
                        shadowElevation = 2.dp,
                    ) {
                        Row(Modifier.padding(horizontal = 10.dp, vertical = 7.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Filled.Place, contentDescription = null, modifier = Modifier.size(16.dp), tint = c.text)
                            Spacer(Modifier.width(6.dp))
                            Text("Open map", style = MaterialTheme.typography.labelMedium, color = c.text)
                        }
                    }
                }
            }
            item {
                Column(Modifier.padding(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 8.dp)) {
                    Text("Your field now", style = MaterialTheme.typography.titleLarge, color = c.text)
                    Text("Today, ${Fmt.date(state.today)}", style = MaterialTheme.typography.bodySmall, color = c.muted)
                }
            }
            // --- the visual summary, first ---
            item {
                Column(
                    Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp)
                        .border(1.dp, c.line, RoundedCornerShape(3.dp))
                        .padding(12.dp)
                        .testTag("glance"),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    val strip = summary.strip
                    if (strip != null) {
                        Column(Modifier.clearAndSetSemantics { contentDescription = strip.spoken }, verticalArrangement = Arrangement.spacedBy(3.dp)) {
                            Text("${strip.year} so far", style = MaterialTheme.typography.labelSmall, color = c.muted)
                            SeasonStripBar(strip.steps, strip.todayStep)
                            MonthTicks()
                            Text(strip.state, style = MaterialTheme.typography.titleSmall, color = c.text)
                        }
                    } else if (state.calendarMissing) {
                        Text("No satellite calendar for this field yet.", style = MaterialTheme.typography.bodySmall, color = c.muted)
                    } else {
                        Skeleton(height = 14.dp); Skeleton(height = 16.dp, widthFraction = 0.5f)
                    }
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(14.dp), verticalArrangement = Arrangement.spacedBy(14.dp), maxItemsInEachRow = 2) {
                        val cell = Modifier.weight(1f).widthIn(min = 140.dp)
                        Meter(summary.rain, "Rain since 1 Oct", cell, unavailable = state.readingsMissing)
                        Meter(summary.waterNeed, "Water need, a year", cell, unavailable = state.rotationMissing)
                        Meter(summary.greenness, "Greenness", cell, unavailable = state.calendarMissing && state.readingsMissing)
                        PercentileTrack(summary.soil, cell, unavailable = !state.partsLoading && summary.soil == null)
                    }
                }
            }
            // --- at most four one-sentence answers ---
            summary.answers.forEachIndexed { i, a ->
                item {
                    if (i > 0) HorizontalDivider(Modifier.padding(horizontal = 16.dp), color = c.lineSoft)
                    val g = glossaryLookup(state.glossary, a.glossaryIds)
                    AnswerBlock(a, onWhatsThis = g?.let { { glossaryOpen = it } })
                }
            }
            if (state.partsLoading && summary.answers.size < 4) item {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Skeleton(height = 12.dp, widthFraction = 0.5f); Skeleton(height = 18.dp, widthFraction = 0.8f); Skeleton(height = 12.dp)
                }
            }
            // --- what you can do next ---
            item { Spacer(Modifier.height(8.dp)); SectionHeading("What you can do next"); Spacer(Modifier.height(6.dp)) }
            item { ActionRow("What's likely this winter", "Rain outlook, water in storage, next season's water need") { onGoTo(FieldTab.Season) } }
            item { ActionRow("Compare rotations", "What you gain and give up, in acre-feet and days") { onGoTo(FieldTab.Compare) } }
            item { ActionRow("Summary for your adviser", "One page, shared as a PDF", primary = true) { onGoTo(FieldTab.Summary) } }
            // --- more detail ---
            item { Spacer(Modifier.height(16.dp)); SectionHeading("More detail", sub = "Everything behind the answers above") }
            item { MoreDetailSections(state) }
        }
    }
    glossaryOpen?.let { g ->
        ModalBottomSheet(onDismissRequest = { glossaryOpen = null }, containerColor = c.paper) {
            Column(Modifier.padding(start = 20.dp, end = 20.dp, bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(g.term, style = MaterialTheme.typography.titleMedium, color = c.text)
                BodyText(g.short)
                g.sourceUrl?.let { SourceLink("Source", it) }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun MoreDetailSections(state: FieldNowUiState) {
    val c = CropLyticsTheme.colors
    val d = state.detail
    Column {
        MoreDetail("About this field", "Soil, water it holds, drainage, salt, slope") {
            d.about.forEach { (k, v) -> LabelValue(k, v, warn = k == "Salt" && v.startsWith("Salty")) }
            Cite("USDA soil survey (SSURGO); NASA NASADEM elevation, 100 ft squares.")
        }
        MoreDetail("Crops grown", state.identity?.recordLine) {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                d.crops.forEach { (y, crop) ->
                    Column(Modifier.clearAndSetSemantics { contentDescription = "$y: $crop" }, horizontalAlignment = Alignment.CenterHorizontally) {
                        Canvas(Modifier.size(width = 26.dp, height = 14.dp)) { drawRect(DataColors.crop(crop)) }
                        Text("'${y % 100}", style = MaterialTheme.typography.labelSmall, color = c.muted)
                    }
                }
            }
            FlowRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                d.crops.map { it.second }.distinct().forEach { crop ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Canvas(Modifier.size(10.dp)) { drawRect(DataColors.crop(crop)) }
                        Text(" $crop", style = MaterialTheme.typography.labelSmall, color = c.text2)
                    }
                }
            }
            Cite("USDA Cropland Data Layer, one crop per year.")
        }
        MoreDetail("Bare, green or flooded", "How to read the season strip") {
            CoverKey()
            BodyText("Each cell is ten days. Green = a full crop canopy; thin = some green (a young crop, regrowth, stubble or weeds); bare = greenness below 0.2 and not under water; hatched = no clear satellite view.")
        }
        if (d.events.isNotEmpty()) MoreDetail("What happened here", "${d.events.size} events near this field") {
            d.events.forEach { e ->
                Column {
                    Text(Fmt.date(e.date), style = MaterialTheme.typography.labelSmall, color = c.muted)
                    Text(e.title, style = MaterialTheme.typography.bodyMedium, color = c.text)
                    e.url?.let { SourceLink("Source", it) }
                }
            }
        }
        MoreDetail("NASA data behind this field", "${d.datasets.count { it.status == "live" }} of ${d.datasets.size} datasets live") {
            d.datasets.forEach { ds ->
                Column(Modifier.padding(vertical = 2.dp)) {
                    Text(ds.name, style = MaterialTheme.typography.labelLarge, color = c.text)
                    ds.tellsYou?.let { BodyText(it) }
                    Cite(listOfNotNull(ds.resolution?.let { "Footprint $it" }, statusWords(ds.status)).joinToString(". ") + ".")
                }
            }
        }
        MoreDetail("Crop-stress weeks", "Weeks the crop looked stressed in past seasons") { Part(d.stress) }
        MoreDetail("Standing water seen", "NASA OPERA surface water on the field") { Part(d.water) }
        MoreDetail("Measured water use", "OpenET, the last five full years") { Part(d.openet) }
        MoreDetail("Machine-learning check", "The bare-field calendar, rule against machine learning") { Part(d.machineLearning) }
        MoreDetail("Crop insurance in the county", "USDA payouts by cause") { Part(d.insurance) }
        MoreDetail("Where every number comes from", "${d.sources.size} sources, NASA first") {
            d.sources.forEach { (title, url) ->
                if (url != null && url.startsWith("http")) SourceLink(title, url) else BodyText(title)
            }
        }
    }
}

private fun statusWords(status: String?) = when (status) {
    "live" -> "Live"
    "pending" -> "Still downloading, not used yet"
    "blocked" -> "Blocked: needs a login we don't have yet"
    else -> null
}

@Composable
private fun Part(p: DetailPart) = when (p) {
    DetailPart.Loading -> Column(verticalArrangement = Arrangement.spacedBy(6.dp)) { Skeleton(height = 12.dp); Skeleton(height = 12.dp, widthFraction = 0.7f) }
    is DetailPart.Unavailable -> DetailUnavailable(p.reason)
    is DetailPart.Lines -> Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        p.lines.dropLast(1).forEach { BodyText(it) }
        p.lines.lastOrNull()?.let { if (p.lines.size > 1) Cite(it) else BodyText(it) }
    }
}

@Composable
fun SourceLink(title: String, url: String) {
    val uri = LocalUriHandler.current
    Text(
        title,
        style = MaterialTheme.typography.bodyMedium.copy(textDecoration = TextDecoration.Underline),
        color = CropLyticsTheme.colors.accent,
        modifier = Modifier
            .clip(RoundedCornerShape(2.dp))
            .clickable(role = Role.Button, onClickLabel = "Open source") { runCatching { uri.openUri(url) } }
            .padding(vertical = 6.dp),
    )
}
