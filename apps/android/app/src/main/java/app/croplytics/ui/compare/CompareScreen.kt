package app.croplytics.ui.compare

import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.croplytics.domain.Fmt
import app.croplytics.domain.LimitFit
import app.croplytics.domain.OptionComparison
import app.croplytics.domain.WaterLimit
import app.croplytics.ui.components.ActionRow
import app.croplytics.ui.components.BodyText
import app.croplytics.ui.components.Cite
import app.croplytics.ui.components.ErrorPanel
import app.croplytics.ui.components.ExampleNote
import app.croplytics.ui.components.HeadBand
import app.croplytics.ui.components.MoreDetail
import app.croplytics.ui.components.OfflineNote
import app.croplytics.ui.components.PageSkeleton
import app.croplytics.ui.components.SectionHeading
import app.croplytics.ui.components.WakingPanel
import app.croplytics.ui.theme.CropLyticsTheme

@Composable
fun CompareScreen(onSummary: () -> Unit, viewModel: CompareViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    CompareContent(state, viewModel::onLimitChange, viewModel::toggleShowAll, viewModel::retry, onSummary)
}

fun fitWords(f: LimitFit) = when (f) {
    LimitFit.Fits -> "fits your limit"
    LimitFit.MayGoOver -> "may go over your limit"
    LimitFit.Over -> "over your limit"
    LimitFit.Unknown -> "no limit set"
}

@Composable
fun CompareContent(
    state: CompareUiState,
    onLimitChange: (Double) -> Unit,
    onToggleAll: () -> Unit,
    onRetry: () -> Unit,
    onSummary: () -> Unit,
) {
    val c = CropLyticsTheme.colors
    val s = state.summary
    when {
        s == null && state.waking -> { WakingPanel(); return }
        s == null && state.error != null -> { ErrorPanel(state.error, onRetry); return }
        s == null -> { PageSkeleton(); return }
    }
    val summary = s!!
    val first = summary.top.firstOrNull()
    val title = first?.let { "${it.name} vs ${summary.today.name.substringBefore(" +").lowercase()} today" } ?: "Your rotation today"
    LazyColumn(Modifier.fillMaxSize().testTag("compare"), contentPadding = app.croplytics.ui.components.pageContentPadding()) {
        state.offlineSavedAt?.let { item { OfflineNote(it) } }
        item { HeadBand(title, null) }
        item { LimitControl(state, onLimitChange) }
        item {
            Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                Text("Today: ${summary.today.name}", style = MaterialTheme.typography.titleSmall, color = c.text)
                Text(
                    (summary.today.need?.let { "${Fmt.one(it.value)} acre-ft/acre a year, ${fitWords(summary.today.fit)}" } ?: "Water need not worked out yet") +
                        (summary.today.bareDays?.let { "; bare about ${it.toInt()} days a year" } ?: ""),
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (summary.today.fit == LimitFit.Over) c.warn else c.text2,
                )
            }
        }
        item { SectionHeading("The two options that score best", sub = if (state.rescoring) "Re-scoring for your limit…" else "Ranked by the rotation model for your limit") }
        summary.top.forEach { o -> item(key = "top-${o.id}") { OptionPanel(o) } }
        item {
            OutlinedButton(
                onClick = onToggleAll,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp).semantics { stateDescription = if (state.showAll) "Shown" else "Hidden" }.testTag("see-all"),
                shape = RoundedCornerShape(3.dp),
            ) {
                Text(if (state.showAll) "Hide other options" else "See all options (${summary.all.size})")
                Spacer(Modifier.width(6.dp))
                Icon(Icons.Filled.KeyboardArrowDown, contentDescription = null, modifier = Modifier.rotate(if (state.showAll) 180f else 0f))
            }
        }
        if (state.showAll) {
            summary.all.forEachIndexed { i, o ->
                item(key = "all-${o.id}") {
                    if (i > 0) HorizontalDivider(Modifier.padding(horizontal = 16.dp), color = c.lineSoft)
                    Column(Modifier.padding(horizontal = 16.dp, vertical = 10.dp)) {
                        Text("${i + 1}. ${o.name}", style = MaterialTheme.typography.titleSmall, color = c.text)
                        Text(
                            (o.need?.let { "${Fmt.one(it.value)} acre-ft/acre (likely ${Fmt.one(it.low)} to ${Fmt.one(it.high)}), ${fitWords(o.fit)}" } ?: "Water need not worked out"),
                            style = MaterialTheme.typography.bodySmall, color = if (o.fit == LimitFit.Over) c.warn else c.text2,
                        )
                        Text(o.fullName, style = MaterialTheme.typography.labelSmall, color = c.muted)
                    }
                }
            }
        }
        item { Spacer(Modifier.height(8.dp)); ActionRow("Summary for your adviser", "Put the best option on one page and share it", primary = true, onClick = onSummary) }
        item { Spacer(Modifier.height(16.dp)); SectionHeading("More detail") }
        item {
            Column {
                MoreDetail("How the options are ranked", "Rule-of-thumb scores, 0 to 100") {
                    state.scoreRows.forEach { r ->
                        Column {
                            Text(r.name, style = MaterialTheme.typography.labelLarge, color = c.text)
                            r.lines.forEach { BodyText(it) }
                        }
                    }
                    summary.tieNote?.let { BodyText(it) }
                    Cite("Rotation model (backend/engine): a rule of thumb from published crop tables, not a forecast of yield or profit.")
                }
                MoreDetail("How good is the water estimate?", "Checked against measured water use") {
                    BodyText(summary.openetLine)
                    Cite("Water need: rotation model with NASA POWER weather, 2015 to 2025, minus rain. Measured: OpenET satellite data for today's crop only; the other rotations use the same method, unchecked.")
                }
                MoreDetail("What better and worse mean here", null) {
                    BodyText("An option only counts as better or worse when its whole likely range sits above or below today's. When the ranges overlap, the inputs aren't precise enough to say, and it is listed as no clear difference.")
                    BodyText("Bare = satellite greenness below 0.2 and not under water. Heavy rain = a day with 1 inch or more while the field is bare.")
                }
            }
        }
    }
}

@Composable
private fun LimitControl(state: CompareUiState, onLimitChange: (Double) -> Unit) {
    val c = CropLyticsTheme.colors
    val limit = state.limit ?: return
    Column(
        Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .border(1.dp, c.line, RoundedCornerShape(3.dp))
            .padding(14.dp)
            .testTag("limit-control"),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text("Your water limit", style = MaterialTheme.typography.bodySmall, color = c.muted)
        Row(verticalAlignment = Alignment.CenterVertically) {
            FilledTonalIconButton(onClick = { onLimitChange(limit - 0.1) }, modifier = Modifier.semantics { contentDescription = "Lower the limit by 0.1" }) {
                Text("−", style = MaterialTheme.typography.titleLarge)
            }
            Text(
                "${Fmt.one(limit)} acre-ft/acre",
                Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite }.testTag("limit-value"),
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                color = c.text,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            )
            FilledTonalIconButton(onClick = { onLimitChange(limit + 0.1) }, modifier = Modifier.semantics { contentDescription = "Raise the limit by 0.1" }) {
                Icon(Icons.Filled.Add, contentDescription = null)
            }
        }
        Slider(
            value = limit.toFloat(),
            onValueChange = { onLimitChange(it.toDouble()) },
            valueRange = WaterLimit.MIN.toFloat()..WaterLimit.MAX.toFloat(),
            modifier = Modifier.semantics { contentDescription = "Water limit, acre-feet per acre a year" },
            colors = SliderDefaults.colors(thumbColor = c.accent, activeTrackColor = c.accent, inactiveTrackColor = c.track),
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (state.limitIsExample) ExampleNote() else Text("Saved for this field", style = MaterialTheme.typography.bodySmall, color = c.muted)
            Spacer(Modifier.weight(1f))
            if (state.rescoring) CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp, color = c.accent)
        }
        if (state.rescoreFailed) Text("Couldn't re-score for this limit; showing the server's default ranking.", style = MaterialTheme.typography.bodySmall, color = c.bad)
    }
}

@Composable
private fun OptionPanel(o: OptionComparison) {
    val c = CropLyticsTheme.colors
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 6.dp)
            .border(1.dp, c.line, RoundedCornerShape(3.dp))
            .padding(14.dp)
            .testTag("option-${o.id}"),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text(o.name, style = MaterialTheme.typography.titleMedium, color = c.text)
        Text(
            o.need?.let { "${Fmt.one(it.value)} acre-ft/acre a year, ${fitWords(o.fit)}" } ?: "Water need not worked out",
            style = MaterialTheme.typography.bodySmall,
            color = if (o.fit == LimitFit.Over) c.warn else c.muted,
        )
        ChangeList("You gain", o.gains.map { it.title to it.amount }, c.good)
        ChangeList("You give up", o.giveUps.map { it.title to it.amount }, c.warn)
        if (o.unclear.isNotEmpty()) {
            Text("No clear difference: ${o.unclear.joinToString(", ")}.", style = MaterialTheme.typography.bodySmall, color = c.muted)
        }
    }
}

@Composable
private fun ChangeList(heading: String, items: List<Pair<String, String>>, color: androidx.compose.ui.graphics.Color) {
    val c = CropLyticsTheme.colors
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(heading, style = MaterialTheme.typography.labelLarge, color = color)
        if (items.isEmpty()) Text("Nothing clear", style = MaterialTheme.typography.bodySmall, color = c.muted)
        items.forEach { (title, amount) ->
            Text(title, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold), color = c.text)
            Text(amount, style = MaterialTheme.typography.bodySmall, color = c.text2)
        }
    }
}
