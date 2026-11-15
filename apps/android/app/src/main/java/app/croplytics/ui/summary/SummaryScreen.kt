package app.croplytics.ui.summary

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.croplytics.domain.AdviserSummary
import app.croplytics.domain.Fmt
import app.croplytics.ui.components.BodyText
import app.croplytics.ui.components.Cite
import app.croplytics.ui.components.ErrorPanel
import app.croplytics.ui.components.HeadBand
import app.croplytics.ui.components.OfflineNote
import app.croplytics.ui.components.PageSkeleton
import app.croplytics.ui.components.WakingPanel
import app.croplytics.ui.theme.CropLyticsTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun SummaryScreen(viewModel: SummaryViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var sharing by remember { mutableStateOf(false) }
    var shareError by remember { mutableStateOf<String?>(null) }
    SummaryContent(
        state = state,
        sharing = sharing,
        shareError = shareError,
        onChoose = viewModel::choose,
        onRetry = viewModel::retry,
        onShare = { s ->
            sharing = true
            shareError = null
            scope.launch {
                runCatching {
                    val file = withContext(Dispatchers.IO) { SummaryPdf.write(context, s) }
                    context.startActivity(SummaryPdf.shareIntent(context, file, "Rotation summary: ${s.fieldName}"))
                }.onFailure { shareError = "Couldn't make the PDF. Try again." }
                sharing = false
            }
        },
    )
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun SummaryContent(
    state: SummaryUiState,
    sharing: Boolean,
    shareError: String?,
    onChoose: (String) -> Unit,
    onRetry: () -> Unit,
    onShare: (AdviserSummary) -> Unit,
) {
    val c = CropLyticsTheme.colors
    val s = state.summary
    when {
        s == null && state.waking -> { WakingPanel(); return }
        s == null && state.error != null -> { ErrorPanel(state.error, onRetry); return }
        s == null -> { PageSkeleton(); return }
    }
    val summary = s!!
    LazyColumn(Modifier.fillMaxSize().testTag("summary"), contentPadding = app.croplytics.ui.components.pageContentPadding()) {
        state.offlineSavedAt?.let { item { OfflineNote(it) } }
        item { HeadBand("Summary for your adviser", "One page: what the field is, what's likely, the option to talk through and what to check locally.") }
        if (state.choices.size > 1) item {
            Column(Modifier.padding(start = 16.dp, end = 16.dp, top = 14.dp)) {
                Text("Option to put on the page", style = MaterialTheme.typography.bodySmall, color = c.muted)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    state.choices.forEach { o ->
                        FilterChip(
                            selected = o.id == state.chosenId,
                            onClick = { onChoose(o.id) },
                            label = { Text(o.name) },
                            shape = RoundedCornerShape(3.dp),
                            colors = FilterChipDefaults.filterChipColors(selectedContainerColor = c.accent, selectedLabelColor = c.onAccent),
                        )
                    }
                }
            }
        }
        item {
            Button(
                onClick = { onShare(summary) },
                enabled = !sharing,
                modifier = Modifier.fillMaxWidth().padding(16.dp).height(52.dp).testTag("share-pdf"),
                shape = RoundedCornerShape(3.dp),
                colors = ButtonDefaults.buttonColors(containerColor = c.accent, contentColor = c.onAccent),
            ) {
                if (sharing) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp, color = c.onAccent)
                else Icon(Icons.Filled.Share, contentDescription = null)
                Spacer(Modifier.width(10.dp))
                Text("Share as PDF", style = MaterialTheme.typography.labelLarge)
            }
            Text(
                shareError ?: "Opens Android's share sheet: email, messages, Drive or print.",
                Modifier.padding(horizontal = 16.dp), style = MaterialTheme.typography.bodySmall,
                color = if (shareError != null) c.bad else c.muted,
            )
            if (state.partial) Text("Some parts are still loading; they will appear on the page as they arrive.", Modifier.padding(horizontal = 16.dp, vertical = 4.dp), style = MaterialTheme.typography.bodySmall, color = c.muted)
        }
        item { PagePreview(summary) }
    }
}

/** On-screen preview of the printed page: same order and words as the PDF. */
@Composable
private fun PagePreview(s: AdviserSummary) {
    val c = CropLyticsTheme.colors
    Column(
        Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .border(1.dp, c.line, RoundedCornerShape(2.dp))
            .background(c.paper),
    ) {
        Column(Modifier.fillMaxWidth().background(c.headBand).padding(14.dp)) {
            Text("Rotation summary for your adviser", style = MaterialTheme.typography.labelSmall, color = c.headInk2)
            Text(s.fieldName, style = MaterialTheme.typography.titleMedium, color = c.headInk)
            Text(s.fieldLine + (s.stateFieldNo?.let { ". State field no. $it" } ?: ""), style = MaterialTheme.typography.labelSmall, color = c.headInk2)
        }
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            PageHeading("This season so far")
            s.now.forEach { a ->
                Text(a.headline, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold), color = if (a.warn) c.warn else c.text)
                BodyText(a.detail)
            }
            PageHeading("What's likely this coming season")
            s.season.forEach { a ->
                Text(a.headline, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold), color = if (a.warn) c.warn else c.text)
                BodyText(a.detail)
            }
            PageHeading("The option to talk through")
            BodyText("Today: ${s.today}")
            s.option?.let { o ->
                Text(o.name + (o.need?.let { ", about ${Fmt.one(it.value)} acre-ft/acre a year" } ?: ""), style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold), color = c.text)
                BodyText("Gains: " + o.gains.joinToString("; ") { "${it.title.lowercase()}, ${it.amount}" }.ifEmpty { "nothing clear" } + ".")
                BodyText("Gives up: " + o.giveUps.joinToString("; ") { "${it.title.lowercase()}, ${it.amount}" }.ifEmpty { "nothing clear" } + ".")
            }
            s.limitLine?.let { Cite(it) }
            PageHeading("What to check locally")
            s.checkLocally.forEach { BodyText("• $it") }
            PageHeading("Sources")
            Cite(s.sources.joinToString("; ") + ".")
            Spacer(Modifier.height(4.dp))
            Cite("Supports, doesn't replace, your adviser. Prepared ${s.preparedOn}.")
        }
    }
}

@Composable
private fun PageHeading(text: String) {
    val c = CropLyticsTheme.colors
    Column(Modifier.padding(top = 6.dp)) {
        Spacer(Modifier.fillMaxWidth().height(1.5.dp).background(c.text))
        Text(text, Modifier.padding(top = 4.dp).semantics { heading() }, style = MaterialTheme.typography.titleSmall, color = c.text)
    }
}
