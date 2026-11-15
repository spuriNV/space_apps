package app.croplytics.ui.field

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.PrimaryScrollableTabRow
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.croplytics.ui.compare.CompareScreen
import app.croplytics.ui.now.FieldNowScreen
import app.croplytics.ui.season.ComingSeasonScreen
import app.croplytics.ui.summary.SummaryScreen
import app.croplytics.ui.theme.CropLyticsTheme
import kotlinx.coroutines.launch

/** The four sections of a field, as text tabs (no icon rail), in the order a grower decides. */
enum class FieldTab(val label: String) {
    Now("Field now"),
    Season("Coming season"),
    Compare("Compare"),
    Summary("Summary"),
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FieldScreen(initialTab: Int, onBack: () -> Unit, onOpenMap: (String) -> Unit, viewModel: FieldViewModel = hiltViewModel()) {
    val c = CropLyticsTheme.colors
    val header by viewModel.header.collectAsStateWithLifecycle()
    val tabs = FieldTab.entries
    val pager = rememberPagerState(initialPage = initialTab.coerceIn(0, tabs.lastIndex)) { tabs.size }
    val scope = rememberCoroutineScope()
    fun goTo(t: FieldTab) = scope.launch { pager.animateScrollToPage(t.ordinal) }

    Scaffold(
        containerColor = c.paper,
        contentWindowInsets = WindowInsets(0),
        topBar = {
            Column(Modifier.background(c.paper)) {
                TopAppBar(
                    navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "All fields") } },
                    title = {
                        Column {
                            Text(
                                header.identity?.name ?: "Loading field…",
                                style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis,
                            )
                            header.identity?.let { Text(it.subtitle, style = MaterialTheme.typography.bodySmall, color = c.muted, maxLines = 1, overflow = TextOverflow.Ellipsis) }
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = c.paper, titleContentColor = c.text, navigationIconContentColor = c.text),
                )
                PrimaryScrollableTabRow(
                    selectedTabIndex = pager.currentPage,
                    containerColor = c.paper,
                    contentColor = c.text,
                    edgePadding = 8.dp,
                    divider = { HorizontalDivider(color = c.line) },
                    indicator = {
                        TabRowDefaults.PrimaryIndicator(
                            Modifier.tabIndicatorOffset(pager.currentPage, matchContentSize = false),
                            width = androidx.compose.ui.unit.Dp.Unspecified,
                            height = 3.dp,
                            color = c.accent,
                            shape = androidx.compose.ui.graphics.RectangleShape,
                        )
                    },
                ) {
                    tabs.forEach { t ->
                        Tab(
                            selected = pager.currentPage == t.ordinal,
                            onClick = { goTo(t) },
                            modifier = Modifier.testTag("tab-${t.name}"),
                            text = { Text(t.label, style = MaterialTheme.typography.labelLarge) },
                            selectedContentColor = c.text,
                            unselectedContentColor = c.muted,
                        )
                    }
                }
                Box(Modifier.fillMaxWidth().height(3.dp).background(c.headBand))
            }
        },
    ) { inner ->
        HorizontalPager(pager, Modifier.padding(inner).fillMaxSize(), beyondViewportPageCount = 0, key = { tabs[it].name }) { page ->
            when (tabs[page]) {
                FieldTab.Now -> FieldNowScreen(onOpenMap = { onOpenMap(viewModel.fieldId) }, onGoTo = ::goTo)
                FieldTab.Season -> ComingSeasonScreen(onCompare = { goTo(FieldTab.Compare) })
                FieldTab.Compare -> CompareScreen(onSummary = { goTo(FieldTab.Summary) })
                FieldTab.Summary -> SummaryScreen()
            }
        }
    }
}
