package app.croplytics.ui.season

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.croplytics.ui.components.ActionRow
import app.croplytics.ui.components.AnswerBlock
import app.croplytics.ui.components.BodyText
import app.croplytics.ui.components.Cite
import app.croplytics.ui.components.ErrorPanel
import app.croplytics.ui.components.HeadBand
import app.croplytics.ui.components.MoreDetail
import app.croplytics.ui.components.OfflineNote
import app.croplytics.ui.components.PageSkeleton
import app.croplytics.ui.components.SectionHeading
import app.croplytics.ui.components.WakingPanel
import app.croplytics.ui.theme.CropLyticsTheme

@Composable
fun ComingSeasonScreen(onCompare: () -> Unit, viewModel: ComingSeasonViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    ComingSeasonContent(state, viewModel::retry, onCompare)
}

@Composable
fun ComingSeasonContent(state: ComingSeasonUiState, onRetry: () -> Unit, onCompare: () -> Unit) {
    val c = CropLyticsTheme.colors
    val s = state.summary
    when {
        s == null && state.waking -> { WakingPanel(); return }
        s == null && state.error != null -> { ErrorPanel(state.error, onRetry); return }
        s == null -> { PageSkeleton(); return }
    }
    val summary = s!!
    PullToRefreshBox(isRefreshing = false, onRefresh = onRetry, modifier = Modifier.fillMaxSize()) {
        LazyColumn(Modifier.fillMaxSize().testTag("coming-season"), contentPadding = PaddingValues(bottom = 32.dp)) {
            state.offlineSavedAt?.let { item { OfflineNote(it) } }
            item { HeadBand("What's likely this winter and next year", summary.lede) }
            summary.items.forEachIndexed { i, a ->
                item {
                    if (i > 0) HorizontalDivider(Modifier.padding(horizontal = 16.dp), color = c.lineSoft)
                    AnswerBlock(a)
                }
            }
            item { Spacer(Modifier.height(4.dp)); ActionRow("Compare rotations", "What each option would need, against your limit", primary = true, onClick = onCompare) }
            item { Spacer(Modifier.height(16.dp)); SectionHeading("More detail") }
            item {
                Column {
                    MoreDetail("Rain and temperature outlook", "Every 3-month outlook NOAA has published") {
                        summary.outlookRows.forEach { r ->
                            Column {
                                Text(r.months, style = MaterialTheme.typography.labelLarge, color = c.text)
                                BodyText("${r.rain}. ${r.temperature}.")
                            }
                        }
                        Cite("Each season is split into a wetter, a middle and a drier third; with no lean each has a 33% chance. 40% means the odds are tilted, not that rain is certain.")
                    }
                    summary.bareWindow?.let {
                        MoreDetail("Longest bare stretch this winter", "When the field is usually bare, and the heavy-rain odds") {
                            BodyText(it)
                            Cite("Longest bare run in this field's satellite calendar each winter, and NOAA station rain 1981 to 2024. Past record, not a forecast.")
                        }
                    }
                    summary.longSummary?.let {
                        MoreDetail("Everything in one paragraph", "The outlook as the data team wrote it") { BodyText(it) }
                    }
                    if (summary.notYetPublished.isNotEmpty()) {
                        MoreDetail("Not published yet", "${summary.notYetPublished.size} outlooks still to come") {
                            summary.notYetPublished.forEach { BodyText(it) }
                        }
                    }
                }
            }
        }
    }
}
