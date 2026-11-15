package app.croplytics.ui.panels

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.material.icons.filled.Print
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.CompareLogic
import app.croplytics.domain.CompareLogic.Weather
import app.croplytics.domain.Fmt
import app.croplytics.domain.Gloss
import app.croplytics.domain.SeasonCalc
import app.croplytics.ui.app.CompareUi
import app.croplytics.ui.app.FieldData
import app.croplytics.ui.app.MainUiState
import app.croplytics.ui.app.MoreDetailButton
import app.croplytics.ui.app.What
import app.croplytics.ui.components.CoverStrip
import app.croplytics.ui.components.ExampleNote
import app.croplytics.ui.components.PageSkeleton
import app.croplytics.ui.components.RangeBars
import app.croplytics.ui.theme.CropLyticsTheme
import kotlin.math.roundToInt

/** Compare callbacks. */
data class CompareActions(
    val pick: (String) -> Unit, val toggleTable: () -> Unit, val toggleTune: () -> Unit, val weather: (Weather) -> Unit,
    val limit: (Double) -> Unit, val weight: (String, Int) -> Unit, val rain: (Double) -> Unit, val heat: (Double) -> Unit, val toBrief: (String) -> Unit,
)

/** "Gain / give up vs today" (ComparePanel.tsx). */
@OptIn(ExperimentalLayoutApi::class)
fun LazyListScope.comparePanel(state: MainUiState, data: FieldData, ui: CompareUi, glossary: Map<String, Pair<String, String>>, a: PanelActions, ca: CompareActions) {
    val base = data.strategies.dataOrNull
    if (base.isNullOrEmpty()) { item(key = "cmp-wait") { PageSkeleton() }; return }
    val strategies: List<StrategyDto> = ui.rescored ?: base
    val limit = data.limit ?: 3.0
    val detail = state.detailOn
    val ctx = CompareLogic.ctx(strategies, data.daily.dataOrNull, data.calendar.dataOrNull?.calendar)
    val today = strategies.firstOrNull { it.isBaseline } ?: strategies.first()
    val allAlts = strategies.filter { it.id != today.id }
    // farmer default: the two best-scoring alternatives; every option with More detail or "See all options"
    val alts = if (detail) allAlts else allAlts.sortedByDescending { it.composite.value ?: 0.0 }.take(2)
    val alt = alts.firstOrNull { it.id == ui.altId } ?: alts.minByOrNull { it.water.irrigationNeedMm?.usable ?: Double.MAX_VALUE } ?: return
    val heavy = data.item.loc.soil?.hydrologicGroup == "D"
    val rows = CompareLogic.rows(alt, today, ui.weather, ctx, strategies, detail, heavy)
    val gains = rows.filter { it.v == CompareLogic.Verdict.Better }; val losses = rows.filter { it.v == CompareLogic.Verdict.Worse }
    val unclear = rows.filter { it.v == CompareLogic.Verdict.Unclear || it.v == CompareLogic.Verdict.Same }; val none = rows.filter { it.v == CompareLogic.Verdict.None }
    val flat = CompareLogic.constantScores(strategies)
    val ranked = strategies.sortedByDescending { it.composite.value ?: 0.0 }
    val tie = ranked.size > 1 && (ranked[0].composite.low ?: 0.0) <= (ranked[1].composite.high ?: 0.0)
    val altW = CompareLogic.water(alt, ui.weather); val todayW = CompareLogic.water(today, ui.weather)

    item(key = "cmp-title") {
        val c = CropLyticsTheme.colors
        Text("${CompareLogic.shortName(alt)} vs ${CompareLogic.shortName(today).substringBefore(" +").replace(Regex("\\s*\\(current\\)$", RegexOption.IGNORE_CASE), "").lowercase()} today",
            Modifier.padding(horizontal = 16.dp, vertical = 8.dp).semantics { heading() }.testTag("compare"), style = MaterialTheme.typography.titleLarge, color = c.text)
    }
    item(key = "cmp-alts") {
        val c = CropLyticsTheme.colors
        Row(Modifier.horizontalScroll(rememberScrollState()).padding(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            alts.forEach { s ->
                val on = s.id == alt.id && !ui.table
                val ms = CompareLogic.monthStrip(s)
                Column(
                    Modifier.width(176.dp).clip(RoundedCornerShape(12.dp)).background(if (on) c.accentContainer else c.raised).border(1.dp, if (on) c.accentOutline else c.lineSoft, RoundedCornerShape(12.dp))
                        .clickable { ca.pick(s.id) }.padding(12.dp).semantics { selected = on }.testTag("alt-${s.id}"),
                ) {
                    Text(CompareLogic.shortName(s), style = MaterialTheme.typography.labelLarge, color = c.text)
                    CoverStrip(ms.cover.flatMap { ch -> listOf(ch, ch, ch) }.joinToString(""), null, Modifier.padding(vertical = 6.dp).clip(RoundedCornerShape(4.dp)), height = 8f)
                    Text("${Fmt.one(CompareLogic.water(s, ui.weather)?.value ?: 0.0)} acre-ft/acre · ${CompareLogic.fits(s, ui.weather, limit).lowercase()}", style = MaterialTheme.typography.labelSmall, color = c.muted)
                }
            }
            Column(
                Modifier.width(150.dp).clip(RoundedCornerShape(12.dp)).background(if (ui.table) c.accentContainer else c.panel2).clickable { ca.toggleTable() }.padding(12.dp).testTag("see-all"),
            ) {
                Text(if (ui.table) "Back to gain / give up" else "See all options", style = MaterialTheme.typography.labelLarge, color = c.accent)
                Text("Every rotation, every factor", style = MaterialTheme.typography.labelSmall, color = c.muted)
            }
        }
    }
    item(key = "cmp-ctl") {
        val c = CropLyticsTheme.colors
        Column(Modifier.fillMaxWidth().padding(16.dp).clip(RoundedCornerShape(12.dp)).background(c.panel2).padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row { Text("Your water limit ", style = MaterialTheme.typography.bodySmall, color = c.muted); Text("${Fmt.one(limit)} acre-ft/acre", style = MaterialTheme.typography.labelLarge, color = c.text, modifier = Modifier.testTag("limit-value")) }
            if (data.exampleLimit) ExampleNote()
            Slider(limit.toFloat(), { ca.limit(it.toDouble()) }, valueRange = 0.5f..6f, modifier = Modifier.semantics { contentDescription = "Water limit, acre-feet per acre a year" }.testTag("alloc"),
                colors = SliderDefaults.colors(thumbColor = c.accent, activeTrackColor = c.accent, inactiveTrackColor = c.track))
            app.croplytics.ui.components.Segmented(Weather.entries.map { it to it.label }, ui.weather, label = "Weather year", onPick = ca.weather)
            if (detail) app.croplytics.ui.components.PillButton(if (ui.tune) "Hide priorities and what-ifs" else "Your priorities, and what if it’s drier or hotter", app.croplytics.ui.components.PillKind.Text, Modifier.testTag("tune"), small = true) { ca.toggleTune() }
        }
    }
    if (ui.tune && detail) item(key = "cmp-tune") {
        val c = CropLyticsTheme.colors
        Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp).testTag("tune-panel"), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("What matters to you", style = MaterialTheme.typography.titleSmall, color = c.text)
            CompareLogic.PRIORITIES.forEach { (k, label) ->
                Text(label, style = MaterialTheme.typography.bodySmall, color = c.text2)
                app.croplytics.ui.components.Segmented(CompareLogic.LEVEL.indices.map { it to CompareLogic.LEVEL[it] }, ui.weights[k] ?: CompareLogic.defaultWeight(k), label = label) { ca.weight(k, it) }
            }
            Text("What if the year is", style = MaterialTheme.typography.titleSmall, color = c.text)
            app.croplytics.ui.components.Segmented(CompareLogic.RAIN, ui.dP, label = "Rain") { ca.rain(it) }
            app.croplytics.ui.components.Segmented(CompareLogic.HEAT, ui.dT, label = "Heat") { ca.heat(it) }
            Text(when { ui.busy -> "Re-scoring…"; ui.custom -> "Water need and ranking below use your settings."; else -> "Default: every priority counts the same, normal weather." }, style = MaterialTheme.typography.bodySmall, color = c.muted)
            Text("Best fit for what matters to you", style = MaterialTheme.typography.titleSmall, color = c.text)
            ranked.forEachIndexed { i, s -> Text("${i + 1}. ${CompareLogic.shortName(s)}${if (s.isBaseline) " (today)" else ""}${if (i == 0 && tie) "  too close to call with the next one" else ""}", style = MaterialTheme.typography.bodySmall, color = c.text) }
        }
    }
    if (!ui.table) {
        item(key = "cmp-gain") { androidx.compose.foundation.layout.Box(Modifier.testTag("cmp-gain-list")) { GainList("You gain", gains, true, "Nothing clearly better than today.") } }
        item(key = "cmp-loss") { GainList("You give up", losses, false, "Nothing clearly worse than today.") }
        item(key = "cmp-side") {
            val c = CropLyticsTheme.colors
            Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Water against your limit", style = MaterialTheme.typography.titleLarge, color = c.text, modifier = Modifier.padding(top = 16.dp))
                What(Gloss.WaterBalance, glossary)
                Text("${CompareLogic.fits(alt, ui.weather, limit)}. Needs ${Fmt.one(altW?.value ?: 0.0)} acre-ft/acre. Your limit: ${Fmt.one(limit)}.", style = MaterialTheme.typography.bodyMedium, color = c.text)
                if (detail) {
                    How("${CompareLogic.rng(CompareLogic.UNIT_METRICS[0], altW).replace("likely", "Likely").let { if (it.isNotEmpty()) "$it acre-ft/acre, " else "" }}${ui.weather.label.lowercase()}. Today needs ${Fmt.one(todayW?.value ?: 0.0)}.${if (Regex("safflower|wheat", RegexOption.IGNORE_CASE).containsMatchIn(alt.name)) " An upper bound: soil water stored over winter is not counted." else ""}")
                    How("${app.croplytics.domain.FieldNowLogic.openetText(base)} That checks crop water use for today’s crop only; irrigation need and the other rotations use the same method, unchecked.")
                    Sub("Bare days"); What(Gloss.Bare, glossary)
                    How("Today: ${ctx.bare[today.id]?.let { "${it.value.roundToInt()} days a year, seen by satellite ${ctx.bareYears.firstOrNull()}–${ctx.bareYears.lastOrNull()}" } ?: "${today.exposure.bareDays?.usable?.roundToInt() ?: "?"} days a year (estimated)"}. Other rotations: estimated by the rotation model. ${SeasonCalc.BARE_DEF}")
                    Sub("No clear difference")
                    How("${unclear.mapIndexed { i, r -> if (i > 0) r.m.label.lowercase() else r.m.label }.joinToString(", ").ifEmpty { "None" }}. The likely ranges overlap, so the inputs aren’t precise enough to say which is better.")
                    Sub("Not scored yet")
                    How((none.map { it.m.label } + CompareLogic.SCORE_METRICS.filter { it.key in flat }.map { it.label } + "Dollars per acre (no price data yet)").mapIndexed { i, x -> if (i > 0) x.lowercase() else x }.joinToString(", ") + ".")
                    How("Bars: the span of likely values; the tick is the best estimate. A gain counts only when the two spans don’t overlap.")
                }
            }
        }
        item(key = "cmp-more") { MoreDetailButton(detail, "All rotations and what-ifs", a.toggleDetail) }
        item(key = "cmp-brief") {
            app.croplytics.ui.components.PillButton("Print this comparison for your adviser", app.croplytics.ui.components.PillKind.Primary, Modifier.fillMaxWidth().padding(16.dp).testTag("to-brief"), icon = androidx.compose.material.icons.Icons.Filled.Print) { ca.toBrief(alt.id) }
        }
    } else {
        item(key = "cmp-table") {
            val c = CropLyticsTheme.colors
            val metrics = CompareLogic.allRows(today, ui.weather, ctx, strategies, heavy)
            Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
                Text("Water, days and weather · ${ui.weather.label.lowercase()}", style = MaterialTheme.typography.labelLarge, color = c.text)
                metrics.forEachIndexed { i, m ->
                    if (i == CompareLogic.UNIT_METRICS.size) Text("Soil, feed and pests · rules of thumb, 0 to 100, higher is better", Modifier.padding(top = 10.dp), style = MaterialTheme.typography.labelLarge, color = c.text)
                    val b = m.get(today, ui.weather, ctx)
                    Column(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                        Text(m.label, style = MaterialTheme.typography.titleSmall, color = c.text)
                        Text("What you do now (${CompareLogic.shortName(today)}): ${CompareLogic.fmt(m, b)} ${CompareLogic.rng(m, b)}", style = MaterialTheme.typography.bodySmall, color = c.text2)
                        allAlts.forEach { s ->
                            val av = m.get(s, ui.weather, ctx); val v = CompareLogic.verdict(av, b, m.higherIsBetter)
                            val word = when (v) { CompareLogic.Verdict.Better -> "Better"; CompareLogic.Verdict.Worse -> "Worse"; CompareLogic.Verdict.None -> "Not scored"; else -> "Can’t tell" }
                            Text("${CompareLogic.shortName(s)}: $word, ${CompareLogic.fmt(m, av)} ${CompareLogic.rng(m, av)}", style = MaterialTheme.typography.bodySmall,
                                color = when (v) { CompareLogic.Verdict.Better -> c.good; CompareLogic.Verdict.Worse -> c.warn; else -> c.text2 })
                        }
                    }
                    HorizontalDivider(color = c.lineSoft)
                }
            }
        }
    }
    item(key = "cmp-foot") { Cite("Better / worse = the whole likely range is above or below today’s. Water need: rotation model with NASA POWER weather, 2015–2025. ${CompareLogic.HEAT_NOTE} Supports, doesn’t replace, your adviser.") }
}

@Composable
private fun GainList(title: String, rows: List<CompareLogic.Row>, gain: Boolean, empty: String) {
    val c = CropLyticsTheme.colors
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(title, style = MaterialTheme.typography.titleLarge, color = if (gain) c.good else c.warn, modifier = Modifier.semantics { heading() })
        if (rows.isEmpty()) Text(empty, style = MaterialTheme.typography.bodySmall, color = c.muted)
        rows.forEach { r ->
            Column {
                Text(if (gain) r.m.gain else r.m.loss, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold), color = c.text)
                Text(CompareLogic.delta(r.m, r.a!!.value, r.b!!.value), style = MaterialTheme.typography.bodySmall, color = c.text2)
                RangeBars(r.b, r.a, gain, r.m.unit == CompareLogic.Unit.SCORE, Modifier.padding(top = 2.dp))
            }
        }
    }
}

