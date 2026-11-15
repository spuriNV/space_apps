package app.croplytics.ui.panels

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.compose.animation.animateContentSize
import app.croplytics.data.repository.FieldRepository
import app.croplytics.data.repository.LoadError
import app.croplytics.data.repository.LoadState
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.Fmt
import app.croplytics.domain.NationLogic
import app.croplytics.ui.components.PillButton
import app.croplytics.ui.components.PillKind
import app.croplytics.ui.components.Skeleton
import app.croplytics.ui.theme.CropLyticsTheme
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.serialization.json.JsonObject
import javax.inject.Inject

/** Gives the Nation tools and salmon cards their data (one small route each, saved on the phone). */
@HiltViewModel
class RouteViewModel @Inject constructor(private val repo: FieldRepository) : ViewModel() {
    fun route(id: String, path: String) = repo.route(id, path)
    fun salmon(id: String) = repo.salmon(id)
}

@Composable
private fun rememberRoute(id: String, path: String?): LoadState<JsonObject> {
    val vm: RouteViewModel = hiltViewModel()
    val flow = remember(id, path) { if (path == null) kotlinx.coroutines.flow.flowOf(LoadState.Loading) else if (path == "salmon") vm.salmon(id) else vm.route(id, path) }
    val st by flow.collectAsState(LoadState.Loading)
    return st
}

@Composable
private fun Quiet(text: String) = Text(text, style = MaterialTheme.typography.bodySmall, color = CropLyticsTheme.colors.muted)

@Composable
private fun CardBox(title: String, tag: String, content: @Composable () -> Unit) {
    val c = CropLyticsTheme.colors
    Column(Modifier.fillMaxWidth().background(c.panel2, RoundedCornerShape(12.dp)).padding(14.dp).animateContentSize().testTag(tag), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(title, Modifier.semantics { heading() }, style = MaterialTheme.typography.titleMedium, color = c.text)
        content()
    }
}

@Composable
private fun <T> Loaded(st: LoadState<JsonObject>, read: (JsonObject) -> T?, what: String, body: @Composable (T) -> Unit) {
    when (st) {
        is LoadState.Ready -> { val v = read(st.data); if (v == null) Quiet("$what is not available for this place yet.") else body(v) }
        is LoadState.Failed -> Quiet(if (st.error == LoadError.NotAvailable) "$what is not available for this place yet." else "$what could not load right now.")
        else -> { Skeleton(height = 14.dp); Skeleton(height = 14.dp, widthFraction = 0.6f) }
    }
}

@Composable
private fun KV(k: String, v: String) {
    val c = CropLyticsTheme.colors
    Row(Modifier.fillMaxWidth()) { Text(k, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = c.muted); Text(v, style = MaterialTheme.typography.labelLarge, color = c.text) }
}

@Composable
private fun Fine(t: String) = Text(t, style = MaterialTheme.typography.labelSmall, color = CropLyticsTheme.colors.muted)

/** "Salmon and the field" for the BC field (Salmon.tsx, short): what the river is doing, in plain lines. Under More detail. */
@Composable
fun SalmonCard(id: String) {
    val c = CropLyticsTheme.colors
    val st = rememberRoute(id, "salmon")
    if (st is LoadState.Failed && st.error == LoadError.NotAvailable) return
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(top = 20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Salmon and the field", Modifier.semantics { heading() }, style = MaterialTheme.typography.titleLarge, color = c.text)
        CardBox("The river this summer", "salmon-card") {
            Loaded(st, NationLogic::salmon, "The salmon summary") { s ->
                s.flowNow?.let { Text(it, style = MaterialTheme.typography.bodyMedium, color = c.text) }
                s.lines.take(4).forEach { Text(it, style = MaterialTheme.typography.bodyMedium, color = c.text2) }
                s.window?.let { w -> Text("Watch ${w}: ${s.windowWhy ?: "the lowest flows of the year."}", style = MaterialTheme.typography.bodySmall, color = c.text2) }
                s.statement?.let { Fine(it) }
                Fine("Water Survey of Canada gauges, BC orders, DFO and NASA records. Public data only.")
            }
        }
    }
}

/** "Nation tools" (NationTools.tsx): land status and nearby Nations up top, four cards load when opened. Hidden when the server has no /nation for this field. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun NationToolsSection(id: String, isBC: Boolean) {
    val c = CropLyticsTheme.colors
    val uri = LocalUriHandler.current
    val st = rememberRoute(id, "nation")
    if (st is LoadState.Failed && st.error == LoadError.NotAvailable) return
    var open by rememberSaveable(id) { mutableStateOf(false) }
    var cutoff by rememberSaveable(id) { mutableStateOf("08-15") }
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp).testTag("nation-tools"), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Nation tools", Modifier.padding(top = 20.dp).semantics { heading() }, style = MaterialTheme.typography.titleLarge, color = c.text)
        Text("Water, land and funding facts for Nations and tribal farm and lands staff. Public data only.", style = MaterialTheme.typography.bodyMedium, color = c.text2)
        Loaded(st, NationLogic::head, "Nation tools") { h ->
            Text(buildString { append(h.landStatus); h.areaName?.let { append(" ($it)") } }, style = MaterialTheme.typography.titleSmall, color = c.text)
            h.near.take(3).forEach { n ->
                Row(Modifier.fillMaxWidth()) {
                    Column(Modifier.weight(1f)) { Text(n.nation, style = MaterialTheme.typography.labelLarge, color = c.text); Text(n.area, style = MaterialTheme.typography.labelSmall, color = c.muted) }
                    Text(if (n.inside) "Inside" else "${NationLogic.miles(n.km)} mi away", style = MaterialTheme.typography.bodySmall, color = c.text2)
                }
            }
            Fine("Listed by distance only. Reserve and trust boundaries are legal lines, not traditional territory.")
            if (h.places.isNotEmpty()) {
                Text("Place names", Modifier.padding(top = 4.dp), style = MaterialTheme.typography.titleSmall, color = c.text)
                h.places.forEach { p ->
                    Text(buildString {
                        append(p.name); p.english?.let { append(" ($it)") }; p.nation?.let { append(", as written by $it") }; append(".")
                        if (p.notConfirmed) append(" Not confirmed by the Nation.")
                    }, Modifier.then(if (p.url != null) Modifier.clickable { runCatching { uri.openUri(p.url) } } else Modifier), style = MaterialTheme.typography.bodySmall, color = c.text2)
                }
            }
            PillButton(if (open) "Hide the tools" else "Open the tools", PillKind.Tonal, small = true, modifier = Modifier.testTag("nation-toggle")) { open = !open }
            if (open) {
                DroughtCard(id, cutoff) { cutoff = it }
                if (isBC) { CardBox("Water and salmon", "nt-groundwater") { Fine("The groundwater tool covers California only. For this valley, the river and fish summary is under More detail."); SalmonLines(id) } }
                else GroundwaterCard(id)
                LandCard(id)
                FundingCard(id, if (isBC) "BC" else "CA", cutoff)
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun DroughtCard(id: String, cutoff: String, setCutoff: (String) -> Unit) {
    val c = CropLyticsTheme.colors
    val st = rememberRoute(id, "nation/drought_rotation?cutoff=$cutoff")
    CardBox("Drought rotation", "nt-drought") {
        Text("If irrigation water stops on", style = MaterialTheme.typography.labelLarge, color = c.text2)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            listOf("07-15", "08-01", "08-15", "09-01", "09-15").forEach { d -> PillButton(NationLogic.mmdd(d), if (d == cutoff) PillKind.Primary else PillKind.Tonal, small = true) { setCutoff(d) } }
        }
        Loaded(st, NationLogic::drought, "The drought rotation") { d ->
            Text("Share of each rotation's crop water use that falls after ${d.cutoffLabel}", style = MaterialTheme.typography.bodyMedium, color = c.text)
            val peak = maxOf(1.0, d.rows.maxOf { it.sharePct })
            d.rows.forEach { r ->
                Column {
                    Row(Modifier.fillMaxWidth()) { Text(r.name + if (r.baseline) " (current)" else "", Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = c.text); Text("${r.sharePct.toInt()}%", style = MaterialTheme.typography.labelLarge, color = c.text) }
                    Row(Modifier.fillMaxWidth().padding(vertical = 2.dp).background(c.track, RoundedCornerShape(3.dp))) { androidx.compose.foundation.layout.Box(Modifier.fillMaxWidth((r.sharePct / peak).toFloat().coerceIn(0.02f, 1f)).padding(vertical = 3.dp).background(c.accent, RoundedCornerShape(3.dp))) }
                    r.dryRank?.let { Fine("Dry-year rank $it of ${d.rows.size}") }
                }
            }
            Fine("A lower share means less of the crop's water is needed once the water stops. Rank 1 does best in a dry year. Estimates from the rotation model, not a guarantee.")
            if (d.scenarios.isNotEmpty()) {
                Text("Other cutoff dates", Modifier.padding(top = 4.dp), style = MaterialTheme.typography.titleSmall, color = c.text)
                d.scenarios.forEach { s -> KV(s.label + if (s.requested) " (shown)" else "", (s.mineUnmet?.let { "${it.toInt()}% unmet" } ?: "–") + (s.lowest?.let { ", lowest ${it.toInt()}%" } ?: "")) }
            }
            d.note?.let { Fine(it) }
        }
    }
}

@Composable
private fun GroundwaterCard(id: String) {
    val c = CropLyticsTheme.colors
    val st = rememberRoute(id, "nation/groundwater")
    CardBox("Groundwater", "nt-groundwater") {
        Loaded(st, NationLogic::groundwater, "Groundwater") { g ->
            Text(g.basin + (g.priority?.let { ", ${it.lowercase()} priority basin" } ?: ""), style = MaterialTheme.typography.bodyMedium, color = c.text)
            if (g.agencies.isNotEmpty()) KV("Groundwater agency", g.agencies.joinToString("; "))
            g.status?.let { KV("SGMA status", it) }
            if (g.latestPctl != null) KV("Groundwater now vs history", "${g.latestPctl}th percentile (50 is usual)") else g.reason?.let { Quiet(it) }
            if (g.pumping.isNotEmpty()) { Text("Pumping need by rotation", Modifier.padding(top = 4.dp), style = MaterialTheme.typography.titleSmall, color = c.text); g.pumping.forEach { KV(it.first, "${Fmt.whole(it.second.toDouble())} acre-ft") } }
            g.note?.let { Fine(it) }
            g.caveat?.let { Fine(it) }
        }
    }
}

@Composable
private fun SalmonLines(id: String) {
    val c = CropLyticsTheme.colors
    val st = rememberRoute(id, "salmon")
    (st.dataOrNull?.let(NationLogic::salmon))?.lines?.take(2)?.forEach { Text(it, style = MaterialTheme.typography.bodyMedium, color = c.text2) }
}

@Composable
private fun LandCard(id: String) {
    val c = CropLyticsTheme.colors
    val uri = LocalUriHandler.current
    val st = rememberRoute(id, "nation/land_season")
    CardBox("Land and season", "nt-land") {
        Loaded(st, { NationLogic.land(it) }, "Land and season") { l ->
            if (l.greenup != null) {
                KV("Green-up (${l.greenYear})", l.greenup); KV("Peak green", l.peak ?: "–"); KV("Green fades", l.fades ?: "–")
            } else Quiet("Green-up dates: ${l.greenReason}")
            l.snowOff?.let { KV("Snow gone from the watershed", it); Fine("NASA MODIS, whole watershed, not the field.") }
            l.fire7?.let { KV("Fire detections, last 7 days", it) }
            l.links.forEach { (t, u) -> Text(t, Modifier.clickable { runCatching { uri.openUri(u) } }.padding(vertical = 8.dp), style = MaterialTheme.typography.bodySmall, color = c.accent) }
            l.note?.let { Fine(it) }
        }
    }
}

@Composable
private fun FundingCard(id: String, jur: String, cutoff: String) {
    val c = CropLyticsTheme.colors
    val uri = LocalUriHandler.current
    val st = rememberRoute(id, "nation/funding?jurisdiction=$jur")
    CardBox("Funding (${if (jur == "BC") "British Columbia and Canada" else "California and US"})", "nt-funding") {
        Loaded(st, NationLogic::funding, "Funding") { f ->
            f.programs.forEach { p ->
                Column(Modifier.padding(top = 6.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Row(Modifier.fillMaxWidth()) {
                        Text(p.name, Modifier.weight(1f).then(if (p.url != null) Modifier.clickable { runCatching { uri.openUri(p.url) } } else Modifier), style = MaterialTheme.typography.labelLarge, color = if (p.url != null) c.accent else c.text)
                        Text(NationLogic.statusWord(p.status), Modifier.padding(start = 8.dp), style = MaterialTheme.typography.labelSmall, color = c.muted)
                    }
                    Fine(p.agency)
                    KV("Typical amount", p.amount)
                    Text("Who can apply: ${p.eligible}", style = MaterialTheme.typography.bodySmall, color = c.text2)
                    p.helps?.let { Text("How CropLytics helps: $it", style = MaterialTheme.typography.bodySmall, color = c.text2) }
                    if (!p.verified) Fine("Details not yet confirmed on the program's own page.")
                    PillButton("Download report", PillKind.Tonal, small = true) {
                        runCatching { uri.openUri("${app.croplytics.BuildConfig.API_BASE_URL}locations/$id/nation/report.pdf?program=${java.net.URLEncoder.encode(p.id, "UTF-8")}&cutoff=$cutoff") }
                    }
                }
            }
            Fine((f.disclaimer?.let { "$it " } ?: "") + "Listing a program does not mean any Nation or agency endorses CropLytics.")
        }
    }
}
