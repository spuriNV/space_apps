package app.croplytics.ui.app

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.BottomSheetScaffold
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SheetValue
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberBottomSheetScaffoldState
import androidx.compose.material3.rememberStandardBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.derivedStateOf
import androidx.compose.foundation.layout.statusBars
import app.croplytics.ui.panels.FieldHeaderBar
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.croplytics.data.repository.LoadState
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.FieldNowLogic
import app.croplytics.domain.Map3D
import app.croplytics.domain.Nasa
import app.croplytics.domain.NasaStatus
import app.croplytics.ui.components.OfflineNote
import app.croplytics.ui.components.WakingPanel
import app.croplytics.ui.map.CropMap
import app.croplytics.ui.map.FootprintLabels
import app.croplytics.ui.map.MapContent
import app.croplytics.ui.map.MapControls
import app.croplytics.ui.map.MapHandle
import app.croplytics.ui.map.StackLabels
import app.croplytics.ui.map.UnderFieldHud
import app.croplytics.ui.panels.CompareActions
import app.croplytics.ui.panels.PanelActions
import app.croplytics.ui.panels.comparePanel
import app.croplytics.ui.panels.fieldNowPanel
import app.croplytics.ui.panels.printPanel
import app.croplytics.ui.panels.seasonPanel
import app.croplytics.ui.panels.yearPanel
import app.croplytics.ui.theme.CropLyticsTheme

private enum class Snap { Peek, Half, Full }

/**
 * The phone layout of the web app (App.tsx at 390 px): the satellite map fills the screen; the field panel is a draggable
 * bottom sheet (peek, half, full); the sections are bottom tabs; the "Viewing" date and Map layers sit under the top bar.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(deepLink: Pair<String, Int>? = null, vm: MainViewModel = hiltViewModel()) {
    val c = CropLyticsTheme.colors
    val state by vm.state.collectAsStateWithLifecycle()
    val field by vm.field.collectAsStateWithLifecycle()
    val compare by vm.compare.collectAsStateWithLifecycle()
    val briefPick by vm.briefPick.collectAsStateWithLifecycle()
    var switchOpen by remember { mutableStateOf(false) }
    var dateOpen by remember { mutableStateOf(false) }
    var sourcesOpen by remember { mutableStateOf(false) }
    val handle = remember { MapHandle() }
    val tick = remember { mutableStateOf(0) }
    var snap by rememberSaveable { mutableStateOf(Snap.Half) }
    val sheetState = rememberStandardBottomSheetState(SheetValue.PartiallyExpanded, skipHiddenState = true)
    val scaffold = rememberBottomSheetScaffoldState(sheetState)
    val density = LocalDensity.current
    val listState = rememberLazyListState()

    LaunchedEffect(deepLink) { deepLink?.let { (id, tab) -> vm.deepLink(id, tab) } }
    // a field or a big section opens the sheet higher, the year replay keeps the map in view
    LaunchedEffect(state.selectedId, state.tab, state.bcOpen) {
        snap = when { state.selectedId == null || state.bcOpen -> Snap.Half; state.tab in setOf(Tab.Season, Tab.Compare, Tab.Print) -> Snap.Full; else -> Snap.Half }
        listState.scrollToItem(0)
    }
    LaunchedEffect(snap) { if (snap == Snap.Full) sheetState.expand() else sheetState.partialExpand() }
    LaunchedEffect(sheetState) { snapshotFlow { sheetState.currentValue }.collect { v -> if (v == SheetValue.Expanded) snap = Snap.Full else if (snap == Snap.Full) snap = Snap.Half } }

    val data = field
    val glossary = data?.glossary?.dataOrNull?.items.orEmpty().associate { it.id to (it.term to it.short) }

    Scaffold(
        containerColor = c.paper,
        contentWindowInsets = WindowInsets(0),
        bottomBar = { BottomTabs(if (state.selectedId != null && state.panelOpen && !state.bcOpen) state.tab else null, state.selectedId != null) { vm.openTab(it) } },
    ) { inner ->
        BoxWithConstraints(Modifier.padding(inner).fillMaxSize()) {
            val screenH = maxHeight
            val layoutHpx = constraints.maxHeight
            // spec 5.2 snaps: peek 128 dp, half 52%, full stops under the top bar
            val peek = if (snap == Snap.Peek) 128.dp else screenH * 0.52f
            val topBarH = 64.dp + with(density) { WindowInsets.statusBars.getTop(this).toDp() }
            BottomSheetScaffold(
                scaffoldState = scaffold,
                sheetPeekHeight = peek,
                sheetContainerColor = c.paper,
                sheetShape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp),
                sheetShadowElevation = 8.dp,
                sheetDragHandle = {
                    Box(
                        Modifier.fillMaxWidth().clickable(role = Role.Button, onClickLabel = "Resize the panel") {
                            snap = when (snap) { Snap.Peek -> Snap.Half; Snap.Half -> Snap.Full; Snap.Full -> Snap.Peek }
                        }.padding(top = 12.dp, bottom = 12.dp).semantics { contentDescription = "Resize the field panel" }.testTag("grab"),
                        contentAlignment = Alignment.Center,
                    ) { Box(Modifier.size(width = 36.dp, height = 4.dp).background(c.outline.copy(alpha = 0.6f), RoundedCornerShape(2.dp))) }
                },
                sheetContent = {
                    val stuck by remember { derivedStateOf { listState.firstVisibleItemIndex > 0 || listState.firstVisibleItemScrollOffset > 8 } }
                    Column(Modifier.fillMaxWidth().height(screenH - topBarH - 8.dp)) {
                        if (data != null && state.selectedId != null && state.panelOpen && !state.bcOpen) {
                            FieldHeaderBar(data, stuck, showActions = state.tab == Tab.Now && snap != Snap.Peek, onClose = vm::closePanel, openTab = vm::openTab)
                        }
                        LazyColumn(Modifier.fillMaxWidth().weight(1f).testTag("sheet"), state = listState, contentPadding = PaddingValues(bottom = 24.dp)) {
                            sheetContent(state, data, compare, briefPick, glossary, vm, onSources = { sourcesOpen = true })
                        }
                    }
                },
            ) { _ ->
                val sheetTopPx = runCatching { sheetState.requireOffset() }.getOrDefault(layoutHpx * 0.54f)
                val visibleSheetPx = (layoutHpx - sheetTopPx).coerceAtLeast(0f)
                val topInsetPx = with(density) { 132.dp.roundToPx() }
                Box(Modifier.fillMaxSize()) {
                    val sel = state.selected
                    val content = remember(state.fields, state.selectedId, data, state.t, state.layersOn) { mapContent(state, data) }
                    CropMap(content, vm.mapCommands, visibleSheetPx.toInt(), topInsetPx, handle, tick, vm::select, vm::goBC, vm::onCamera, Modifier.fillMaxSize().testTag("map"))
                    if (sel != null) {
                        FootprintLabels(handle, tick, content.footprints)
                        StackLabels(handle, tick, content.stack, sel.rings, sel.id.lat, topInsetPx)
                    }
                    Column(Modifier.fillMaxWidth().align(Alignment.TopCenter)) {
                        TopBar(state, vm::goHome, { switchOpen = true }, { dateOpen = true }, { vm.setLayersOpen(true) })
                        if (!state.isToday) DateBanner(state.t, vm::backToToday, Modifier.align(Alignment.CenterHorizontally).padding(top = 10.dp))
                        if (state.drilled) UnderFieldHud(Modifier.padding(start = 12.dp, top = 8.dp))
                        if (sel != null && !state.panelOpen) app.croplytics.ui.components.PillButton(sel.id.name, app.croplytics.ui.components.PillKind.Tonal, Modifier.padding(start = 12.dp, top = 10.dp), small = true, onClick = vm::reopenPanel)
                    }
                    MapControls(
                        state.camera.bearing, state.camera.pitch,
                        onHome = vm::goHome, onNorth = { vm.map(MapCommand.ResetNorth) }, onTilt = { vm.map(MapCommand.Toggle3D) }, onZoom = { vm.map(MapCommand.ZoomBy(it)) },
                        modifier = Modifier.align(Alignment.TopEnd).offset { IntOffset(0, (sheetTopPx - with(density) { 260.dp.toPx() }).toInt().coerceAtLeast(topInsetPx + 8)) }.padding(end = 12.dp),
                    )
                }
            }
        }
    }

    if (switchOpen) FieldSwitcher(state, vm::select, vm::goBC, vm::goHome) { switchOpen = false }
    if (dateOpen) DateSheet(state, vm.quickDates, vm.years, vm::setT, vm::toggleEarlier) { dateOpen = false }
    if (state.layersOpen) LayersSheet(state.layersOn, state.selected?.loc?.areaHa?.value, vm::toggleLayer) { vm.setLayersOpen(false) }
    if (sourcesOpen) SourcesSheet { sourcesOpen = false }
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
    return MapContent(fields, state.selectedId, stack, fps)
}

/** What the sheet shows: BC, the pick list, or the selected field's section. */
private fun androidx.compose.foundation.lazy.LazyListScope.sheetContent(
    state: MainUiState, data: FieldData?, compare: CompareUi, briefPick: String?, glossary: Map<String, Pair<String, String>>, vm: MainViewModel, onSources: () -> Unit,
) {
    if (state.bcOpen) { item(key = "bc") { BCCard(vm::closeBC) }; return }
    if (state.selectedId == null || data == null) {
        fieldPicker(state, vm::onQuery, vm::toggleFamily, vm::clearFilters, vm::select, vm::goBC, vm::retry)
        return
    }
    if (!state.panelOpen) { item(key = "closed") { Text("Panel closed. Tap the field name above the map to open it again.", Modifier.padding(16.dp), color = CropLyticsTheme.colors.muted) }; return }
    if (data.waking) item(key = "waking") { WakingPanel() }
    data.offlineSavedAt?.let { item(key = "offline") { OfflineNote(it) } }
    val a = PanelActions(vm::setT, vm::backToToday, vm::toggleDetail, vm::drill, onSources, vm::openTab, vm::closePanel)
    when (state.tab) {
        Tab.Now -> {
            val cal = data.calendar.dataOrNull?.calendar
            val loading = data.parts.any { it is LoadState.Loading || it is LoadState.Waking }
            val view = FieldNowLogic.build(
                data.item.loc, cal, data.regional.dataOrNull, data.nasaNow.dataOrNull, data.strategies.dataOrNull, data.daily.dataOrNull, data.openet.dataOrNull,
                data.stress.dataOrNull, data.water.dataOrNull, data.limit, data.exampleLimit, state.t, state.todayT, loading,
            )
            val used = buildMap {
                if (cal != null) { put("landsat", NasaStatus.Live); if (cal.hls) put("hls", NasaStatus.Live) }
                data.regional.dataOrNull?.let { r -> if (r.soilSource == "smap") put("smap", NasaStatus.Live); if (r.hasGroundwater || r.soilSource == "grace_da") put("grace", NasaStatus.Live) }
                if (data.nasaNow.dataOrNull?.readings?.containsKey("imerg_wy_to_date_mm") == true) put("imerg", NasaStatus.Live)
                if (data.strategies.dataOrNull != null) put("power", NasaStatus.Live)
                if (data.water.dataOrNull?.scenes?.isNotEmpty() == true || data.regional.dataOrNull?.dswx?.isNotEmpty() == true) put("opera", NasaStatus.Live)
                if (data.item.loc.terrain?.slopeMeanPct?.value != null) put("nasadem", NasaStatus.Live)
            }
            val nasa = Nasa.list(data.item.loc.nasaDatasets, data.item.loc.datasets.mapValues { it.value.status }, used)
            fieldNowPanel(state, data, view, nasa, glossary, a)
        }
        Tab.Season -> seasonPanel(state, data, glossary, a)
        Tab.Year -> yearPanel(state, data, a, vm::togglePlay, vm::toggleEarlier)
        Tab.Compare -> comparePanel(state, data, compare, glossary, a, CompareActions(vm::comparePick, vm::compareTable, vm::compareTune, vm::compareWeather, vm::setLimit, vm::compareWeight, vm::compareRain, vm::compareHeat, vm::toBrief))
        Tab.Print -> printPanel(state, data, briefPick, vm::pickBrief)
    }
}
