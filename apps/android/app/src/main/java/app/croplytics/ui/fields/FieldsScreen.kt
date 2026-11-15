package app.croplytics.ui.fields

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.croplytics.ui.components.ErrorPanel
import app.croplytics.ui.components.FieldThumbnail
import app.croplytics.ui.components.OfflineNote
import app.croplytics.ui.components.Skeleton
import app.croplytics.ui.components.WakingPanel
import app.croplytics.ui.theme.CropLyticsTheme

@Composable
fun FieldsScreen(onOpenField: (String) -> Unit, viewModel: FieldsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    FieldsContent(state, viewModel::onQueryChange, viewModel::retry, onOpenField)
}

/** Stateless list so it can be previewed and tested without a server. */
@Composable
fun FieldsContent(state: FieldsUiState, onQuery: (String) -> Unit, onRetry: () -> Unit, onOpenField: (String) -> Unit) {
    val c = CropLyticsTheme.colors
    Scaffold(
        containerColor = c.paper,
        contentWindowInsets = WindowInsets(0),
        topBar = { WordmarkBar() },
    ) { inner ->
        PullToRefreshBox(isRefreshing = state.refreshing, onRefresh = onRetry, modifier = Modifier.padding(inner).fillMaxSize()) {
            LazyColumn(Modifier.fillMaxSize().testTag("fields-list"), contentPadding = PaddingValues(bottom = 24.dp)) {
                state.offlineSavedAt?.let { item { OfflineNote(it) } }
                item {
                    Column(Modifier.padding(start = 16.dp, end = 16.dp, top = 18.dp, bottom = 6.dp)) {
                        Text("Pick your field", style = MaterialTheme.typography.headlineSmall, color = c.text, modifier = Modifier.semantics { heading() })
                        Text(
                            if (state.totalFields > 0) "${state.totalFields} California fields, each with NASA Earth data behind it." else "California fields with NASA Earth data behind them.",
                            style = MaterialTheme.typography.bodyMedium, color = c.muted,
                        )
                    }
                }
                item { SearchBox(state.query, onQuery) }
                when {
                    state.waking -> item { WakingPanel() }
                    state.error != null -> item { ErrorPanel(state.error, onRetry) }
                    state.loading -> items(4) { RowSkeleton() }
                    state.rows.isEmpty() -> item {
                        Text(
                            "No field matches \"${state.query}\". Try a town, a county or a crop.",
                            Modifier.padding(16.dp), style = MaterialTheme.typography.bodyMedium, color = c.muted,
                        )
                    }
                    else -> items(state.rows, key = { it.identity.id }) { row ->
                        FieldRowItem(row, onClick = { onOpenField(row.identity.id) })
                        HorizontalDivider(Modifier.padding(start = 16.dp), color = c.lineSoft)
                    }
                }
                item {
                    Text(
                        "Why not British Columbia yet? The ground records needed to check a tool like this are not there yet, so we built and checked it in California first.",
                        Modifier.padding(start = 16.dp, end = 16.dp, top = 20.dp).navigationBarsPadding(),
                        style = MaterialTheme.typography.bodySmall, color = c.muted,
                    )
                }
            }
        }
    }
}

/** Solid paper bar with the wordmark, a hairline and a 3 dp spot-green band under it. */
@Composable
fun WordmarkBar() {
    val c = CropLyticsTheme.colors
    Column(Modifier.fillMaxWidth().background(c.paper).statusBarsPadding()) {
        Text(
            "CropLytics",
            Modifier.padding(horizontal = 16.dp, vertical = 12.dp).semantics { heading() },
            style = MaterialTheme.typography.headlineSmall,
            color = c.accent,
        )
        HorizontalDivider(color = c.line)
        Box(Modifier.fillMaxWidth().height(3.dp).background(c.headBand))
    }
}

@Composable
private fun SearchBox(query: String, onQuery: (String) -> Unit) {
    val c = CropLyticsTheme.colors
    val focus = LocalFocusManager.current
    OutlinedTextField(
        value = query,
        onValueChange = onQuery,
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp).testTag("field-search"),
        placeholder = { Text("Search by town, county or crop") },
        leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
        trailingIcon = {
            if (query.isNotEmpty()) IconButton(onClick = { onQuery("") }) { Icon(Icons.Filled.Clear, contentDescription = "Clear search") }
        },
        singleLine = true,
        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
        keyboardActions = androidx.compose.foundation.text.KeyboardActions(onSearch = { focus.clearFocus() }),
        shape = RoundedCornerShape(3.dp),
        colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = c.accent, unfocusedBorderColor = c.line),
    )
}

@Composable
private fun FieldRowItem(row: FieldRow, onClick: () -> Unit) {
    val c = CropLyticsTheme.colors
    val id = row.identity
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(role = Role.Button, onClickLabel = "Open field", onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .testTag("field-row-${id.id}"),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        FieldThumbnail(row.rings, Modifier.size(width = 104.dp, height = 78.dp).clip(RoundedCornerShape(2.dp)))
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(id.name, style = MaterialTheme.typography.titleSmall, color = c.text)
            Text(id.subtitle, style = MaterialTheme.typography.bodySmall, color = c.text2)
            Text(id.recordLine, style = MaterialTheme.typography.labelSmall, color = c.muted)
        }
        Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = c.muted)
    }
}

@Composable
private fun RowSkeleton() {
    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(width = 104.dp, height = 78.dp)) { Skeleton(height = 78.dp) }
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Skeleton(height = 16.dp, widthFraction = 0.85f)
            Skeleton(height = 12.dp, widthFraction = 0.6f)
            Skeleton(height = 10.dp, widthFraction = 0.75f)
        }
    }
}
