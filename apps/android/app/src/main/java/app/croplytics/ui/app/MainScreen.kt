package app.croplytics.ui.app

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animate
import androidx.compose.animation.core.spring
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.Orientation
import androidx.compose.foundation.gestures.draggable
import androidx.compose.foundation.gestures.rememberDraggableState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Layers
import androidx.compose.material.icons.filled.Navigation
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.Velocity
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.croplytics.data.repository.LoadState
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.FieldNowLogic
import app.croplytics.domain.FieldNowView
import app.croplytics.domain.Map3D
import app.croplytics.domain.Nasa
import app.croplytics.domain.NasaStatus
import app.croplytics.ui.components.IconDisc
import app.croplytics.ui.components.OfflineNote
import app.croplytics.ui.components.WakingPanel
import app.croplytics.ui.components.focusRing
import app.croplytics.ui.map.CropMap
import app.croplytics.ui.map.FootprintLabels
import app.croplytics.ui.map.MapContent
import app.croplytics.ui.map.MapHandle
import app.croplytics.ui.map.StackLabels
import app.croplytics.ui.map.UnderFieldHud
import app.croplytics.ui.panels.CompareActions
import app.croplytics.ui.panels.FieldHeaderBar
import app.croplytics.ui.panels.PanelActions
import app.croplytics.ui.panels.comparePanel
import app.croplytics.ui.panels.fieldNowPanel
import app.croplytics.ui.panels.printPanel
import app.croplytics.ui.panels.seasonPanel
import app.croplytics.ui.panels.yearPanel
import app.croplytics.ui.theme.CropLyticsTheme
import app.croplytics.ui.theme.LocalReduceMotion
import kotlinx.coroutines.launch
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

enum class Snap { Peek, Half, Full }

/**
 * Map-first phone layout: the satellite map fills the screen edge to edge; a floating search bar on top opens a
 * full-screen search; thumb-sized map buttons (viewing date, layers, 3D, home); the field lives in a draggable sheet
 * (128 dp peek with the field name and one key line, half, full) with its sections as pills inside the sheet.
 * Back closes search, then collapses the sheet, then leaves the field.
 */
@Composable
fun MainScreen(deepLink: Pair<String, Int>? = null, vm: MainViewModel = hiltViewModel()) {
    val c = CropLyticsTheme.colors
    val state by vm.state.collectAsStateWithLifecycle()
    val field by vm.field.collectAsStateWithLifecycle()
    val compare by vm.compare.collectAsStateWithLifecycle()
    val briefPick by vm.briefPick.collectAsStateWithLifecycle()
    var dateOpen by remember { mutableStateOf(false) }
    var sourcesOpen by remember { mutableStateOf(false) }
    val handle = remember { MapHandle() }
    val tick = remember { mutableStateOf(0) }
    var snap by rememberSaveable { mutableStateOf(Snap.Half) }
    var settleNonce by remember { mutableIntStateOf(0) }
    val density = LocalDensity.current
    val reduce = LocalReduceMotion.current
    val listState = rememberLazyListState()
    val data = field

    LaunchedEffect(deepLink) { deepLink?.let { (id, tab) -> vm.deepLink(id, tab) } }
    LaunchedEffect(state.selectedId, state.tab, state.bcOpen) {
        snap = when { state.selectedId == null || state.bcOpen -> Snap.Half; state.tab in setOf(Tab.Season, Tab.Compare, Tab.Print) -> Snap.Full; else -> Snap.Half }
        settleNonce++
        listState.scrollToItem(0)
    }
    // Back: search, then the sheet, then the field, then the app
    BackHandler(enabled = state.searchOpen || snap != Snap.Peek || state.selectedId != null || state.bcOpen) {
        when {
            state.searchOpen -> vm.setSearchOpen(false)
            snap != Snap.Peek -> { snap = Snap.Peek; settleNonce++ }
            state.bcOpen -> vm.closeBC()
            else -> vm.goHome()
        }
    }

    // light status bar icons over the map (with a scrim), dark ones on the paper search screen and the full sheet
    val view = androidx.compose.ui.platform.LocalView.current
    val darkTheme = androidx.compose.foundation.isSystemInDarkTheme()
    androidx.compose.runtime.SideEffect {
        (view.context as? android.app.Activity)?.window?.let { w ->
            androidx.core.view.WindowCompat.getInsetsController(w, view).isAppearanceLightStatusBars = !darkTheme && (state.searchOpen || snap == Snap.Full)
        }
    }
    val glossary = data?.glossary?.dataOrNull?.items.orEmpty().associate { it.id to (it.term to it.short) }
    // heavy panel maths runs once per input change, never on map moves
    val nowView: FieldNowView? = remember(data, state.t, state.todayT) {
        data?.let {
            FieldNowLogic.build(
                it.item.loc, it.calendar.dataOrNull?.calendar, it.regional.dataOrNull, it.nasaNow.dataOrNull, it.strategies.dataOrNull, it.daily.dataOrNull, it.openet.dataOrNull,
                it.stress.dataOrNull, it.water.dataOrNull, it.limit, it.exampleLimit, state.t, state.todayT, it.parts.any { p -> p is LoadState.Loading || p is LoadState.Waking },
            )
        }
    }
    val content = remember(state.fields, state.selectedId, data, state.t, state.layersOn) { mapContent(state, data) }

    BoxWithConstraints(Modifier.fillMaxSize().background(c.paper)) {
        val h = constraints.maxHeight.toFloat()
        val statusPx = WindowInsets.statusBars.getTop(density).toFloat()
        val navPx = WindowInsets.navigationBars.getBottom(density).toFloat()
        val fullTop = statusPx + with(density) { 76.dp.toPx() }
        val halfTop = h * 0.48f
        val peekTop = h - navPx - with(density) { 128.dp.toPx() }
        fun anchor(s: Snap) = when (s) { Snap.Full -> fullTop; Snap.Half -> halfTop; Snap.Peek -> peekTop }
        val topState = remember { mutableFloatStateOf(halfTop) }
        var top by topState
        var settledTop by remember { mutableFloatStateOf(halfTop) }
        val scope = androidx.compose.runtime.rememberCoroutineScope()
        var flingV by remember { mutableFloatStateOf(0f) }

        LaunchedEffect(snap, settleNonce, h) {
            val target = anchor(snap)
            if (reduce) top = target
            else animate(top, target, flingV, spring(dampingRatio = 0.86f, stiffness = Spring.StiffnessMediumLow)) { v, _ -> top = v }
            flingV = 0f; settledTop = target
        }
        fun settle(velocity: Float) {
            val order = listOf(Snap.Full, Snap.Half, Snap.Peek)
            val target = when {
                velocity < -1200f -> order.lastOrNull { anchor(it) < top - 1 } ?: Snap.Full
                velocity > 1200f -> order.firstOrNull { anchor(it) > top + 1 } ?: Snap.Peek
                else -> order.minBy { abs(anchor(it) - top) }
            }
            flingV = velocity; snap = target; settleNonce++
        }
        val atAnchor = { Snap.entries.any { abs(anchor(it) - top) < 1f } }
        val nested = remember(fullTop, peekTop) {
            object : NestedScrollConnection {
                override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset {
                    val dy = available.y
                    if (dy < 0 && topState.floatValue > fullTop + 0.5f) {
                        val nt = max(fullTop, topState.floatValue + dy); val used = nt - topState.floatValue; topState.floatValue = nt
                        if (nt <= fullTop + 0.5f) { snap = Snap.Full; settledTop = fullTop }
                        return Offset(0f, used)
                    }
                    return Offset.Zero
                }
                override fun onPostScroll(consumed: Offset, available: Offset, source: NestedScrollSource): Offset {
                    val dy = available.y
                    if (dy > 0 && source == NestedScrollSource.UserInput) {
                        val nt = min(peekTop, topState.floatValue + dy); val used = nt - topState.floatValue; topState.floatValue = nt; return Offset(0f, used)
                    }
                    return Offset.Zero
                }
                override suspend fun onPreFling(available: Velocity): Velocity {
                    if (!atAnchor()) { settle(available.y); return available }
                    return Velocity.Zero
                }
                override suspend fun onPostFling(consumed: Velocity, available: Velocity): Velocity {
                    if (!atAnchor()) { settle(available.y); return available }
                    return Velocity.Zero
                }
            }
        }
        val drag = rememberDraggableState { d -> top = (top + d).coerceIn(fullTop, peekTop) }

        // ---------- map, edge to edge ----------
        val sel = state.selected
        CropMap(content, vm.mapCommands, (h - top).toInt(), (statusPx + with(density) { 72.dp.toPx() }).toInt(), handle, tick, vm::select, vm::goBC, vm::onCamera, Modifier.fillMaxSize().testTag("map"))
        if (sel != null) {
            FootprintLabels(handle, tick, content.footprints)
            StackLabels(handle, tick, content.stack, sel.rings, sel.id.lat, (statusPx + with(density) { 72.dp.toPx() }).toInt())
            app.croplytics.ui.map.ReserveLabels(handle, tick, content.reserves)
        }

        // a soft scrim so the status bar icons read over imagery
        Box(Modifier.fillMaxWidth().height(with(density) { statusPx.toDp() } + 24.dp).background(androidx.compose.ui.graphics.Brush.verticalGradient(listOf(androidx.compose.ui.graphics.Color.Black.copy(alpha = 0.38f), androidx.compose.ui.graphics.Color.Transparent))))
        // ---------- floating search bar, date pill, legend ----------
        Column(Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal = 12.dp, vertical = 8.dp)) {
            SearchBarPill(onClick = { vm.setSearchOpen(true) })
            if (!state.isToday) DateBanner(state.t, vm::backToToday, Modifier.align(Alignment.CenterHorizontally).padding(top = 8.dp))
            if (state.drilled) UnderFieldHud(Modifier.padding(top = 8.dp))
        }

        // ---------- thumb-sized map buttons above the sheet ----------
        MapButtons(vm, onDate = { dateOpen = true }, modifier = Modifier.align(Alignment.TopEnd).offset { IntOffset(0, (top - with(density) { 248.dp.toPx() }).roundToInt().coerceAtLeast((statusPx + with(density) { 80.dp.toPx() }).roundToInt())) }.padding(end = 12.dp))

        // ---------- the sheet ----------
        val sheetH = with(density) { (h - fullTop).toDp() }
        Column(
            Modifier.fillMaxWidth().height(sheetH).offset { IntOffset(0, (top - fullTop).roundToInt() + fullTop.roundToInt()) }
                .shadow(10.dp, RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp)).clip(RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp))
                .background(c.paper).nestedScroll(nested).testTag("sheet"),
        ) {
            val stuck by remember { derivedStateOf { listState.firstVisibleItemIndex > 0 || listState.firstVisibleItemScrollOffset > 8 } }
            Column(Modifier.fillMaxWidth().draggable(drag, Orientation.Vertical, onDragStopped = { v -> settle(v) })) {
                // grabber: tap cycles peek > half > full; the chevron collapses or expands
                Box(Modifier.fillMaxWidth().heightIn(min = 28.dp)) {
                    Box(
                        Modifier.align(Alignment.Center).width(96.dp).height(28.dp).clickable(role = Role.Button, onClickLabel = "Resize the panel") {
                            snap = when (snap) { Snap.Peek -> Snap.Half; Snap.Half -> Snap.Full; Snap.Full -> Snap.Peek }; settleNonce++
                        }.semantics { contentDescription = "Resize the panel" }.testTag("grab"),
                        contentAlignment = Alignment.Center,
                    ) { Box(Modifier.size(width = 36.dp, height = 4.dp).background(c.outline.copy(alpha = 0.6f), RoundedCornerShape(2.dp))) }
                    IconDisc(
                        if (snap == Snap.Peek) "Expand the panel" else "Collapse the panel", Modifier.align(Alignment.CenterEnd).padding(end = 4.dp).testTag("collapse"),
                        icon = if (snap == Snap.Peek) Icons.Filled.KeyboardArrowUp else Icons.Filled.KeyboardArrowDown, ghost = true,
                    ) { snap = if (snap == Snap.Peek) Snap.Half else Snap.Peek; settleNonce++ }
                }
                if (data != null && state.selectedId != null && state.panelOpen && !state.bcOpen) {
                    FieldHeaderBar(data, stuck || snap == Snap.Peek, showActions = false, onClose = vm::goHome, openTab = vm::openTab)
                    if (snap != Snap.Peek) SectionTabs(state.tab) { vm.openTab(it) }
                }
            }
            // the part of the sheet below the screen edge plus the gesture bar, so the last item always scrolls into view
            val pad = with(density) { (max(top, settledTop) - fullTop + navPx).toDp() } + 24.dp
            val listAlpha = if (snap == Snap.Peek && abs(top - peekTop) < 2f) 0f else 1f
            LazyColumn(Modifier.fillMaxWidth().weight(1f).graphicsLayer { alpha = listAlpha }, state = listState, contentPadding = PaddingValues(bottom = pad)) {
                sheetContent(state, data, nowView, compare, briefPick, glossary, vm, onSources = { sourcesOpen = true })
            }
        }

        // ---------- full-screen search ----------
        AnimatedVisibility(state.searchOpen, enter = fadeIn() + slideInVertically { -it / 8 }, exit = fadeOut() + slideOutVertically { -it / 8 }) {
            SearchScreen(state, vm)
        }
    }

    if (dateOpen) DateSheet(state, vm.quickDates, vm.years, vm::setT, vm::toggleEarlier) { dateOpen = false }
    if (state.layersOpen) LayersSheet(state.layersOn, state.selected?.loc?.areaHa?.value, vm::toggleLayer, showReserves = state.selected?.loc?.isBC == true) { vm.setLayersOpen(false) }
    if (sourcesOpen) SourcesSheet { sourcesOpen = false }
}

/** Material 3 style search bar floating over the map. */
@Composable
private fun SearchBarPill(onClick: () -> Unit) {
    val c = CropLyticsTheme.colors
    Row(
        Modifier.fillMaxWidth().height(56.dp).shadow(6.dp, CircleShape).clip(CircleShape).background(c.raised).focusRing()
            .clickable(role = Role.Button, onClickLabel = "Search fields or places", onClick = onClick).padding(horizontal = 20.dp).testTag("search-bar"),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Filled.Search, null, tint = c.text2)
        Spacer(Modifier.width(14.dp))
        Text("Search fields or places", Modifier.weight(1f), style = MaterialTheme.typography.bodyLarge, color = c.muted, maxLines = 1)
        Text("CropLytics", style = MaterialTheme.typography.titleSmall, color = c.accent)
    }
}

/** Full-screen search: every field with the crop chips, British Columbia and the whole state. */
@Composable
private fun SearchScreen(state: MainUiState, vm: MainViewModel) {
    val c = CropLyticsTheme.colors
    Surface(Modifier.fillMaxSize().testTag("search-screen"), color = c.paper) {
        Column(Modifier.statusBarsPadding()) {
            Row(Modifier.fillMaxWidth().padding(start = 4.dp, end = 12.dp, top = 8.dp, bottom = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                IconDisc("Close search", icon = Icons.AutoMirrored.Filled.ArrowBack, ghost = true) { vm.setSearchOpen(false) }
                SearchPill(state.query, vm::onQuery, "Search fields or places", Modifier.weight(1f).testTag("search"))
            }
            val nav = WindowInsets.navigationBars.getBottom(LocalDensity.current)
            LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = with(LocalDensity.current) { nav.toDp() } + 24.dp)) {
                fieldPicker(state, vm::onQuery, vm::toggleFamily, vm::clearFilters, vm::select, { vm.setSearchOpen(false); vm.goBC() }, vm::retry, showTitle = false)
                item(key = "search-ca") {
                    Row(Modifier.fillMaxWidth().clickable { vm.setSearchOpen(false); vm.goHome() }.padding(16.dp)) {
                        Icon(Icons.Filled.Home, null, tint = c.text2); Spacer(Modifier.width(12.dp))
                        Column { Text("California", style = MaterialTheme.typography.titleSmall, color = c.text); Text("Back to the whole state", style = MaterialTheme.typography.bodySmall, color = c.muted) }
                    }
                }
            }
        }
    }
}

/** The field's sections as pills inside the sheet; they scroll sideways, so labels never truncate. */
@Composable
private fun SectionTabs(selected: Tab, onTab: (Tab) -> Unit) {
    val c = CropLyticsTheme.colors
    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 12.dp, vertical = 6.dp).testTag("section-tabs"), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Tab.entries.forEach { t ->
            val on = t == selected
            Text(
                t.label, Modifier.heightIn(min = 40.dp).clip(CircleShape).background(if (on) c.accentContainer else c.panel2).focusRing()
                    .clickable(role = Role.Tab) { onTab(t) }.semantics { this.selected = on }.padding(horizontal = 16.dp, vertical = 10.dp).testTag("mtab-${t.name}"),
                style = MaterialTheme.typography.labelMedium, color = if (on) c.onAccentContainer else c.text2, maxLines = 1, softWrap = false,
            )
        }
    }
}

/** Thumb-sized floating map buttons: viewing date, layers, 3D, home, and north when the map is turned. */
@Composable
private fun MapButtons(vm: MainViewModel, onDate: () -> Unit, modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    val cam by vm.camera.collectAsStateWithLifecycle()
    Column(modifier, verticalArrangement = Arrangement.spacedBy(10.dp), horizontalAlignment = Alignment.End) {
        @Composable
        fun Btn(desc: String, tag: String, onClick: () -> Unit, content: @Composable () -> Unit) = Surface(
            onClick = onClick, modifier = Modifier.size(52.dp).semantics { contentDescription = desc }.testTag(tag), shape = CircleShape, color = c.raised, shadowElevation = 6.dp,
        ) { Box(contentAlignment = Alignment.Center) { content() } }
        Btn("Viewing date", "date-control", onDate) { Icon(Icons.Filled.CalendarMonth, null, tint = c.text) }
        Btn("Map layers", "layers-btn", { vm.setLayersOpen(true) }) { Icon(Icons.Filled.Layers, null, tint = c.text) }
        Btn(if (cam.pitch > 5) "Flat 2D view" else "Tilt to 3D", "tilt", { vm.map(MapCommand.Toggle3D) }) { Text(if (cam.pitch > 5) "2D" else "3D", style = MaterialTheme.typography.labelLarge, color = c.text) }
        if (abs(cam.bearing) > 1) Btn("Reset north", "north", { vm.map(MapCommand.ResetNorth) }) { Icon(Icons.Filled.Navigation, null, tint = c.text, modifier = Modifier.rotate(-cam.bearing.toFloat())) }
        Btn("Whole of California", "home", vm::goHome) { Icon(Icons.Filled.Home, null, tint = c.text) }
    }
}

/** Fields, pins, footprints and the 3D stack for the viewing date. */
private fun mapContent(state: MainUiState, data: FieldData?): MapContent {
    val fields = state.fields.dataOrNull.orEmpty()
    val sel = state.selected
    val stack = if (sel != null && data != null && data.item.id.id == sel.id.id) {
        val grid = data.grid.dataOrNull; val cal = data.calendar.dataOrNull?.calendar
        if (grid != null && cal != null) Map3D.stack(sel.rings, sel.id.lat, sel.loc.areaHa?.value ?: 60.0, grid, Map3D.offsets(grid), cal, data.regional.dataOrNull, state.t, state.layersOn) else null
    } else null
    val fps = if (sel != null) Map3D.footprints(sel.rings, sel.id.lon, sel.id.lat, state.layersOn, data?.regional?.dataOrNull?.soilSource == "smap") else emptyList()
    val reserves = if (sel?.loc?.isBC == true && state.layersOn["reserves"] == true) data?.reserves?.dataOrNull.orEmpty() else emptyList()
    return MapContent(fields, state.selectedId, stack, fps, reserves)
}

/** What the sheet shows: BC, the pick list, or the selected field's section. */
private fun androidx.compose.foundation.lazy.LazyListScope.sheetContent(
    state: MainUiState, data: FieldData?, nowView: FieldNowView?, compare: CompareUi, briefPick: String?, glossary: Map<String, Pair<String, String>>, vm: MainViewModel, onSources: () -> Unit,
) {
    if (state.bcOpen) { item(key = "bc") { BCCard(vm::closeBC) }; return }
    if (state.selectedId == null || data == null) {
        fieldPicker(state, vm::onQuery, vm::toggleFamily, vm::clearFilters, vm::select, vm::goBC, vm::retry)
        return
    }
    if (data.waking) item(key = "waking") { WakingPanel() }
    data.offlineSavedAt?.let { item(key = "offline") { OfflineNote(it) } }
    val a = PanelActions(vm::setT, vm::backToToday, vm::toggleDetail, vm::drill, onSources, vm::openTab, vm::goHome)
    when (state.tab) {
        Tab.Now -> {
            val cal = data.calendar.dataOrNull?.calendar
            val used = buildMap {
                if (cal != null) { put("landsat", NasaStatus.Live); if (cal.hls) put("hls", NasaStatus.Live) }
                data.regional.dataOrNull?.let { r -> if (r.soilSource == "smap") put("smap", NasaStatus.Live); if (r.hasGroundwater || r.soilSource == "grace_da") put("grace", NasaStatus.Live) }
                if (data.nasaNow.dataOrNull?.readings?.containsKey("imerg_wy_to_date_mm") == true) put("imerg", NasaStatus.Live)
                if (data.strategies.dataOrNull != null) put("power", NasaStatus.Live)
                if (data.water.dataOrNull?.scenes?.isNotEmpty() == true || data.regional.dataOrNull?.dswx?.isNotEmpty() == true) put("opera", NasaStatus.Live)
                if (data.item.loc.terrain?.slopeMeanPct?.value != null) put("nasadem", NasaStatus.Live)
            }
            val nasa = Nasa.list(data.item.loc.nasaDatasets, data.item.loc.datasets.mapValues { it.value.status }, used)
            if (nowView != null) fieldNowPanel(state, data, nowView, nasa, glossary, a)
        }
        Tab.Season -> seasonPanel(state, data, glossary, a)
        Tab.Year -> yearPanel(state, data, a, vm::togglePlay, vm::toggleEarlier)
        Tab.Compare -> comparePanel(state, data, compare, glossary, a, CompareActions(vm::comparePick, vm::compareTable, vm::compareTune, vm::compareWeather, vm::setLimit, vm::compareWeight, vm::compareRain, vm::compareHeat, vm::toBrief))
        Tab.Print -> printPanel(state, data, briefPick, vm::pickBrief)
    }
}
