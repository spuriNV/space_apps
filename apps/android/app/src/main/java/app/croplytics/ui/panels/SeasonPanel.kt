package app.croplytics.ui.panels

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.croplytics.data.repository.LoadState
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.Gloss
import app.croplytics.domain.SeasonLogic
import app.croplytics.domain.Timeline
import app.croplytics.ui.app.FieldData
import app.croplytics.ui.app.MainUiState
import app.croplytics.ui.app.MoreDetailButton
import app.croplytics.ui.app.What
import app.croplytics.ui.components.ActionRow
import app.croplytics.ui.components.HeadBand
import app.croplytics.ui.theme.CropLyticsTheme

/** "Coming season: what's likely this winter and next year" (ComingSeason.tsx). */
fun LazyListScope.seasonPanel(state: MainUiState, data: FieldData, glossary: Map<String, Pair<String, String>>, a: PanelActions) {
    val o = data.outlook.dataOrNull
    val notReady = data.outlook is LoadState.Failed
    val v = SeasonLogic.build(
        data.item.loc, o, data.nasaNow.dataOrNull, data.regional.dataOrNull, data.strategies.dataOrNull.orEmpty(), data.calendar.dataOrNull?.calendar,
        data.daily.dataOrNull, data.limit ?: 3.0, data.exampleLimit, state.todayT, notReady,
    )
    item(key = "cs-head") { HeadBand("Coming season: what’s likely this winter and next year", "${v.headline}.${v.outlookTag?.let { " $it" } ?: ""}", Modifier.testTag("coming-season")) }
    item(key = "cs-sum") {
        Column(Modifier.testTag("season-summary")) {
            listOf("Winter rain" to v.winterRain, "Water supply" to v.supply, "Next season, today’s rotation" to v.nextNeed).forEachIndexed { i, (h, t) ->
                if (i > 0) HorizontalDivider(Modifier.padding(horizontal = 16.dp), color = CropLyticsTheme.colors.lineSoft)
                Column(Modifier.padding(horizontal = 16.dp, vertical = 10.dp)) {
                    Text(h, style = MaterialTheme.typography.titleSmall, color = CropLyticsTheme.colors.text, modifier = Modifier.semantics { heading() })
                    Text(t, style = MaterialTheme.typography.bodyMedium, color = CropLyticsTheme.colors.text2)
                }
            }
        }
    }
    item(key = "cs-more") { MoreDetailButton(state.detailOn, "Outlooks, reservoirs, every rotation", a.toggleDetail) }
    if (!state.detailOn) return
    item(key = "cs-outlook") {
        Section("Rain and temperature outlook") {
            v.outlookRows.forEach { (m, t) -> Row(Modifier.padding(vertical = 3.dp)) { Text(m, Modifier.width(64.dp), style = MaterialTheme.typography.labelLarge, color = CropLyticsTheme.colors.text); Body(t) } }
            How("Each season is split into a wetter, a middle and a drier third. With no lean each has a 33% chance; 40% means the odds are tilted, not that rain is certain.")
            Cite("NOAA Climate Prediction Center 3-month outlooks${v.issued?.let { ", issued ${Timeline.fmtDate(it)}" } ?: ""}, at this field.")
            Sub("Drought")
            Facts(listOf("Now" to v.droughtNow, "Outlook" to v.droughtOutlook))
            Cite("US Drought Monitor (county) and NOAA seasonal drought outlook.")
        }
    }
    item(key = "cs-water") {
        Section("Water in storage now") {
            if (v.reservoirs.isEmpty()) Body("Not loaded.")
            v.reservoirs.forEach { (n, t) -> Column(Modifier.padding(vertical = 3.dp)) { Text(n, style = MaterialTheme.typography.labelLarge, color = CropLyticsTheme.colors.text); Body(t) } }
            Cite("California Data Exchange Center (CDEC), ${v.reservoirDate?.let(Timeline::fmtDate) ?: "latest"}; “average” is CDEC’s own for the date.")
            Sub("Water in the ground going into winter")
            Facts(listOf("Rain since 1 Oct" to v.rainSince, "Root-zone soil" to v.rootSoil, "Groundwater" to v.groundwater))
            Cite(v.soilCite)
            Sub("Water allocations")
            v.allocationsLead?.let { Body(it) }
            if (v.storageRows.isNotEmpty()) {
                How("What Shasta storage in mid November has meant for the next year’s farm allocation before:")
                Table(listOf("Mid Nov of", "Shasta full", "Next year, south of Delta farms", "Settlement contractors"), v.storageRows + listOfNotNull(v.shastaNow?.let { listOf("${Timeline.yearOf(state.todayT)}, now", it, "not announced yet", "") }))
            }
            Cite("Reclamation CVP allocation table; storage from CDEC.")
            Sub("Snowpack and spring runoff")
            How(v.snow)
        }
    }
    item(key = "cs-bare") {
        Section("Longest bare stretch this winter") {
            What(Gloss.Bare, glossary)
            Text(v.bareTitle, style = MaterialTheme.typography.titleSmall, color = CropLyticsTheme.colors.text)
            if (v.bareText.isNotEmpty()) Body(v.bareText)
            Cite(v.bareCite)
            Sub("Irrigation need next season, by rotation")
            Table(
                listOfNotNull("Rotation", if (o?.irrigation2027 != null) "With the outlook" else null, "Typical year", "Dry like 2022", "Wet like 2023"),
                v.needRows.map { r -> listOfNotNull(r.name + if (r.today) " (today)" else "", if (o?.irrigation2027 != null) (r.outlook ?: "–") else null, r.typical, r.dry, r.wet) },
                warnCells = v.needRows.map { r -> listOfNotNull(false, if (o?.irrigation2027 != null) r.outlookOver else null, r.typicalOver, false, false) },
            )
            How(v.needNote)
            Cite("Rotation model driven by NASA POWER sun, wind and humidity, weather 2015–2025. Safflower and wheat are upper bounds (stored soil water not counted).")
        }
    }
    item(key = "cs-compare") { ActionRow("Compare rotations", "What each option would need, against your limit", primary = true) { a.openTab(app.croplytics.ui.app.Tab.Compare) } }
}

@Composable
internal fun Section(title: String, content: @Composable () -> Unit) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        HorizontalDivider(color = CropLyticsTheme.colors.text, thickness = 2.dp)
        Text(title, style = MaterialTheme.typography.titleMedium, color = CropLyticsTheme.colors.text, modifier = Modifier.semantics { heading() })
        content()
    }
}
@Composable internal fun Sub(t: String) = Text(t, Modifier.padding(top = 8.dp).semantics { heading() }, style = MaterialTheme.typography.titleSmall, color = CropLyticsTheme.colors.text)
@Composable internal fun Body(t: String) = Text(t, style = MaterialTheme.typography.bodyMedium, color = CropLyticsTheme.colors.text2)
@Composable internal fun How(t: String) = Text(t, style = MaterialTheme.typography.bodySmall, color = CropLyticsTheme.colors.text2)
@Composable internal fun Cite(t: String) = Text(t, style = MaterialTheme.typography.labelSmall, color = CropLyticsTheme.colors.muted)
@Composable internal fun Facts(rows: List<Pair<String, String>>) = Column { rows.forEach { (k, v) -> Row(Modifier.padding(vertical = 2.dp)) { Text(k, Modifier.width(110.dp), style = MaterialTheme.typography.bodySmall, color = CropLyticsTheme.colors.muted); Text(v, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = CropLyticsTheme.colors.text) } } }

/** A small table that wraps on a phone; [warnCells] marks values over the limit in brown. */
@Composable
internal fun Table(head: List<String>, rows: List<List<String>>, warnCells: List<List<Boolean>> = emptyList()) {
    val c = CropLyticsTheme.colors
    Column(Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().background(c.panel2).padding(vertical = 4.dp)) { head.forEachIndexed { i, h -> Text(h, Modifier.weight(if (i == 0) 1.6f else 1f).padding(horizontal = 3.dp), style = MaterialTheme.typography.labelSmall, color = c.muted) } }
        rows.forEachIndexed { ri, r ->
            Row(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                r.forEachIndexed { i, v ->
                    val warn = warnCells.getOrNull(ri)?.getOrNull(i) == true
                    Text(v, Modifier.weight(if (i == 0) 1.6f else 1f).padding(horizontal = 3.dp), style = MaterialTheme.typography.bodySmall.copy(fontWeight = if (i == 0) FontWeight.SemiBold else FontWeight.Normal), color = if (warn) c.warn else c.text)
                }
            }
            HorizontalDivider(color = c.lineSoft)
        }
    }
}
