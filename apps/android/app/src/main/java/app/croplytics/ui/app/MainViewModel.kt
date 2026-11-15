package app.croplytics.ui.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.croplytics.data.remote.dto.GlossaryDto
import app.croplytics.data.remote.dto.InsuranceDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.NasaNowDto
import app.croplytics.data.remote.dto.OpenEtDto
import app.croplytics.data.remote.dto.OutlookDto
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.remote.dto.StressDto
import app.croplytics.data.remote.dto.WaterSeenDto
import app.croplytics.data.repository.CalendarBundle
import app.croplytics.data.repository.FieldRepository
import app.croplytics.data.repository.IssPhoto
import app.croplytics.data.repository.LoadState
import app.croplytics.data.repository.dataOrNull
import app.croplytics.data.repository.map
import app.croplytics.domain.CellGrid
import app.croplytics.domain.Daily
import app.croplytics.domain.FieldIdentity
import app.croplytics.domain.FieldNames
import app.croplytics.domain.MapDatasets
import app.croplytics.domain.RegionalSeries
import app.croplytics.domain.Rings
import app.croplytics.domain.Timeline
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.Clock
import java.time.LocalDate
import javax.inject.Inject
import kotlin.math.roundToInt

/** The sections, as the web app's tabs (bottom tabs on a phone). */
enum class Tab(val label: String, val short: String) {
    Now("Field now", "Now"), Season("Coming season", "Season"), Year("This field’s year", "Year"), Compare("Compare", "Compare"), Print("Print for your adviser", "Print"),
}

/** One row of the pick list / one pin on the map. */
data class FieldItem(val loc: LocationDto, val id: FieldIdentity, val rings: Rings)

/** Camera moves the map performs (MapView.tsx MapHandle). */
sealed interface MapCommand {
    /** Fly to a field; carries its centre so the map needs nothing else (a deep link can arrive before the map has the list). */
    data class FlyToField(val id: String, val mode: Mode, val lat: Double = 0.0, val lon: Double = 0.0, val small: Boolean = false) : MapCommand { enum class Mode { Card, Drill, Year } }
    data object FlyHome : MapCommand
    data class FlyTo(val lat: Double, val lon: Double, val zoom: Double) : MapCommand
    data class ZoomBy(val delta: Double) : MapCommand
    data object ResetNorth : MapCommand
    data object Toggle3D : MapCommand
}

data class CameraView(val zoom: Double = 5.75, val pitch: Double = 0.0, val bearing: Double = 0.0, val lat: Double = 37.35, val lon: Double = -119.9)

/** Quick dates in the grower's words for the "Viewing" control (App.tsx QUICK). */
data class QuickDate(val label: String, val sub: String, val t: Int)

data class MainUiState(
    val fields: LoadState<List<FieldItem>> = LoadState.Loading,
    val strips: Map<String, Map<Int, String>> = emptyMap(),
    val query: String = "",
    val family: String? = null,
    val selectedId: String? = null,
    val tab: Tab = Tab.Now,
    /** The field panel is shown (the web's "card"); false after it is closed until a pin or tab reopens it. */
    val panelOpen: Boolean = true,
    val t: Int = 0,
    val todayT: Int = 0,
    val showEarlier: Boolean = false,
    val playing: Boolean = false,
    /** The app-wide "More detail" switch. */
    val detailOn: Boolean = false,
    val layersOn: Map<String, Boolean> = MapDatasets.DEFAULT_ON,
    val layersOpen: Boolean = false,
    val bcOpen: Boolean = false,
    /** Zoomed in under the selected field (the 3D stack is up); updated only when it flips, not on every camera move. */
    val drilledFlag: Boolean = false,
    /** Full-screen search over fields and places. */
    val searchOpen: Boolean = false,
) {
    val isToday get() = t == todayT
    val selected: FieldItem? get() = (fields as? LoadState.Ready)?.data?.firstOrNull { it.id.id == selectedId }
    /** Zoomed in under the selected field: the 3D stack is up. */
    val drilled get() = selectedId != null && drilledFlag
    val families: List<Pair<String, Int>>
        get() = (fields.dataOrNull.orEmpty()).groupingBy { it.id.region.takeIf { r -> r == "bc" } ?: it.id.family }.eachCount()
            .filterKeys { it in setOf("rice", "forage", "bc") }.toList().sortedBy { listOf("rice", "forage", "bc").indexOf(it.first) }
    val shown: List<FieldItem>
        get() {
            val words = query.lowercase().split(Regex("\\s+")).filter(String::isNotBlank)
            return fields.dataOrNull.orEmpty().filter { f ->
                val fam = if (f.id.region == "bc") "bc" else f.id.family
                (family == null || fam == family) && words.all { w ->
                    "${f.id.name} ${f.id.county} county ${f.id.latestCrop} ${f.loc.water?.district.orEmpty()}".lowercase().contains(w)
                }
            }
        }
}

/** Compare's own choices (ComparePanel.tsx local state) and the priorities / what-if re-score. */
data class CompareUi(
    val altId: String? = null,
    val weather: app.croplytics.domain.CompareLogic.Weather = app.croplytics.domain.CompareLogic.Weather.Typical,
    val table: Boolean = false,
    val tune: Boolean = false,
    val weights: Map<String, Int> = emptyMap(),
    val dP: Double = 0.0,
    val dT: Double = 0.0,
    /** Rotations re-scored for the priorities and what-ifs (null = the default scoring). */
    val rescored: List<StrategyDto>? = null,
    val busy: Boolean = false,
) {
    val custom get() = weights.isNotEmpty() || dP != 0.0 || dT != 0.0
}

/** Everything the panels need for the selected field; each part loads on its own. */
data class FieldData(
    val item: FieldItem,
    val calendar: LoadState<CalendarBundle> = LoadState.Loading,
    val regional: LoadState<RegionalSeries> = LoadState.Loading,
    val nasaNow: LoadState<NasaNowDto> = LoadState.Loading,
    /** GET /strategies re-scored for the water limit (POST /score), with the OpenET check kept from GET. */
    val strategies: LoadState<List<StrategyDto>> = LoadState.Loading,
    val daily: LoadState<Daily> = LoadState.Loading,
    val grid: LoadState<CellGrid> = LoadState.Loading,
    val outlook: LoadState<OutlookDto> = LoadState.Loading,
    val openet: LoadState<OpenEtDto> = LoadState.Loading,
    val stress: LoadState<StressDto> = LoadState.Loading,
    val insurance: LoadState<InsuranceDto> = LoadState.Loading,
    val water: LoadState<WaterSeenDto> = LoadState.Loading,
    val iss: LoadState<IssPhoto?> = LoadState.Loading,
    val glossary: LoadState<GlossaryDto> = LoadState.Loading,
    /** BC only: the First Nations card and reserve outlines (context). */
    val firstNations: LoadState<app.croplytics.data.remote.dto.FirstNationsDto> = LoadState.Failed(app.croplytics.data.repository.LoadError.NotAvailable),
    val reserves: LoadState<List<app.croplytics.domain.Reserve>> = LoadState.Failed(app.croplytics.data.repository.LoadError.NotAvailable),
    val limit: Double? = null,
    val exampleLimit: Boolean = true,
) {
    val parts: List<LoadState<*>> get() = listOf(calendar, regional, nasaNow, strategies, daily, outlook)
    val waking get() = parts.any { it is LoadState.Waking }
    val offlineSavedAt get() = parts.filterIsInstance<LoadState.Ready<*>>().filter { it.offline }.minOfOrNull { it.savedAt }
}

@OptIn(ExperimentalCoroutinesApi::class, FlowPreview::class)
@HiltViewModel
class MainViewModel @Inject constructor(
    private val repository: FieldRepository,
    private val clock: Clock,
) : ViewModel() {
    private val today = LocalDate.now(clock)
    val todayT = Timeline.todayT(today)
    val tMax = Timeline.tMax(today)
    val years = Timeline.years(today)

    private val ui = MutableStateFlow(MainUiState(t = todayT, todayT = todayT))
    private val reload = MutableStateFlow(0)
    /** One-shot camera moves for the map, kept until the map is ready to take them (a deep link arrives before the map). */
    private val commands = kotlinx.coroutines.channels.Channel<MapCommand>(capacity = 16, onBufferOverflow = BufferOverflow.DROP_OLDEST)
    val mapCommands: Flow<MapCommand> = commands.receiveAsFlow()
    private var playJob: Job? = null

    /** Quick picks: today, last summer, last spring, the 2023 floods, the 2022 drought. */
    val quickDates: List<QuickDate> = listOf(
        QuickDate("Today", Timeline.when_(todayT), todayT),
        QuickDate("Last summer", "Jul ${lastSummerYear()}", Timeline.tOf(lastSummerYear(), 19)),
        QuickDate("Last spring", "Apr ${lastSpringYear()}", Timeline.tOf(lastSpringYear(), 10)),
        QuickDate("2023 floods", "Mar 2023", Timeline.tOf(2023, 7)),
        QuickDate("2022 drought", "Jul 2022", Timeline.tOf(2022, 19)),
    )
    private fun lastSummerYear() = if (Timeline.stepOf(todayT) >= 19) today.year else today.year - 1
    private fun lastSpringYear() = if (Timeline.stepOf(todayT) >= 10) today.year else today.year - 1

    private val fields: Flow<LoadState<List<FieldItem>>> = reload.flatMapLatest { n -> repository.locations(force = n > 0) }
        .map { s -> s.map { list -> list.map { FieldItem(it, FieldNames.identity(it), it.geometry?.rings().orEmpty()) } } }

    /** 2023 to this year per field, for the pick list; each arrives on its own. */
    private val strips: Flow<Map<String, Map<Int, String>>> = fields.map { s -> s.dataOrNull.orEmpty().map { it.id.id } }.distinctUntilChanged()
        .flatMapLatest { ids ->
            if (ids.isEmpty()) flowOf(emptyMap())
            else combine(ids.map { id -> repository.strip(id).map { id to it.dataOrNull } }) { arr -> arr.mapNotNull { (id, s) -> s?.let { id to it } }.toMap() }
        }

    val state: StateFlow<MainUiState> = combine(ui, fields, strips) { u, f, s -> u.copy(fields = f, strips = s) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), ui.value)

    private val selectedItem: Flow<FieldItem?> = state.map { it.selected }.distinctUntilChanged { a, b -> a?.id?.id == b?.id?.id && a?.loc == b?.loc }

    /** The grower's limit, else the example limit for the field's family (rice 5.0, forage 3.0). */
    private fun limitFlow(item: FieldItem): Flow<Pair<Double, Boolean>> = repository.waterLimit(item.id.id).map { saved ->
        (saved ?: exampleLimit(item)) to (saved == null)
    }

    val field: StateFlow<FieldData?> = selectedItem.flatMapLatest { item ->
        if (item == null) return@flatMapLatest flowOf(null)
        val id = item.id.id
        val limit = limitFlow(item).distinctUntilChanged()
        val base = repository.strategies(id)
        val scored = limit.debounce(450).distinctUntilChanged().flatMapLatest { (lim, _) -> repository.score(id, lim) }
        val strategies = combine(base, scored) { b, sc ->
            val keep = b.dataOrNull?.associateBy { it.id }.orEmpty()
            val merged = sc.dataOrNull?.map { s ->
                val prev = keep[s.id]
                if (s.water.etcVsOpenetPct?.usable != null || prev == null) s
                else s.copy(water = s.water.copy(etcVsOpenetPct = prev.water.etcVsOpenetPct, openetEtMmSeason = prev.water.openetEtMmSeason))
            }
            if (merged != null) LoadState.Ready(merged, (sc as LoadState.Ready).savedAt, sc.offline) else b
        }
        val core = combine(repository.calendar(id), repository.regional(id), repository.nasaNow(id), strategies, limit) { c, r, n, s, l ->
            FieldData(item, calendar = c, regional = r, nasaNow = n, strategies = s, limit = l.first, exampleLimit = l.second)
        }
        val more = combine(repository.daily(id), repository.grid(id), repository.outlook(id), repository.openet(id), repository.stress(id)) { d, g, o, oe, st ->
            listOf(d, g, o, oe, st)
        }
        val bc = item.loc.isBC
        val none: Flow<LoadState<Nothing>> = flowOf(LoadState.Failed(app.croplytics.data.repository.LoadError.NotAvailable))
        val more2 = combine(repository.insurance(id), repository.waterSeen(id), repository.iss(id), repository.glossary(),
            if (bc) repository.firstNations(id) else none) { i, w, iss, gl, fn -> listOf(i, w, iss, gl, fn) }
        val reserves = if (bc) repository.reserves(id) else none
        @Suppress("UNCHECKED_CAST")
        combine(core, more, more2, reserves) { c, m, m2, rs ->
            c.copy(
                daily = m[0] as LoadState<Daily>, grid = m[1] as LoadState<CellGrid>, outlook = m[2] as LoadState<OutlookDto>,
                openet = m[3] as LoadState<OpenEtDto>, stress = m[4] as LoadState<StressDto>,
                insurance = m2[0] as LoadState<InsuranceDto>, water = m2[1] as LoadState<WaterSeenDto>, iss = m2[2] as LoadState<IssPhoto?>,
                glossary = m2[3] as LoadState<GlossaryDto>,
                firstNations = m2[4] as LoadState<app.croplytics.data.remote.dto.FirstNationsDto>,
                reserves = rs as LoadState<List<app.croplytics.domain.Reserve>>,
            )
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    // ---------------- events ----------------

    fun select(id: String) {
        ui.update { it.copy(selectedId = id, panelOpen = true, bcOpen = false, searchOpen = false, tab = if (it.selectedId == null) Tab.Now else it.tab) }
        fly(id, MapCommand.FlyToField.Mode.Card)
    }

    private fun fly(id: String, mode: MapCommand.FlyToField.Mode) {
        val f = state.value.fields.dataOrNull?.firstOrNull { it.id.id == id }
            ?: (ui.value.fields.dataOrNull)?.firstOrNull { it.id.id == id }
        commands.trySend(MapCommand.FlyToField(id, mode, f?.id?.lat ?: 0.0, f?.id?.lon ?: 0.0, (f?.loc?.areaHa?.value ?: 60.0) < 45))
    }

    /** Back to the whole state and the pick list (the wordmark / home button). */
    fun goHome() {
        ui.update { it.copy(selectedId = null, tab = Tab.Now, bcOpen = false, panelOpen = true) }
        commands.trySend(MapCommand.FlyHome)
    }

    fun goBC() {
        ui.update { it.copy(bcOpen = true) }
        commands.trySend(MapCommand.FlyTo(49.9, -121.0, 6.4))
    }
    fun closeBC() = ui.update { it.copy(bcOpen = false) }

    fun openTab(tab: Tab) {
        if (ui.value.selectedId == null) return
        ui.update { it.copy(tab = tab, panelOpen = true) }
        val id = ui.value.selectedId!!
        if (tab == Tab.Year && cameraState.value.zoom > 13.2) fly(id, MapCommand.FlyToField.Mode.Year)
    }

    fun closePanel() = ui.update { it.copy(panelOpen = false) }
    fun reopenPanel() = ui.update { it.copy(panelOpen = true) }

    /** "Look under the field in 3D": fly in, tilt, and the stack rises. */
    fun drill() { ui.value.selectedId?.let { fly(it, MapCommand.FlyToField.Mode.Drill) } }

    fun onQuery(q: String) = ui.update { it.copy(query = q) }
    fun toggleFamily(f: String) = ui.update { it.copy(family = if (it.family == f) null else f) }
    fun clearFilters() = ui.update { it.copy(query = "", family = null) }

    fun setT(t: Int) { stopPlaying(); ui.update { it.copy(t = t.coerceIn(0, tMax).coerceAtMost(todayT)) } }
    fun backToToday() = setT(todayT)
    fun toggleEarlier() = ui.update { it.copy(showEarlier = !it.showEarlier) }

    /** Replay on the map: step through the 10-day steps (220 ms each), looping from the first shown year. */
    fun togglePlay() {
        if (ui.value.playing) { stopPlaying(); return }
        ui.update { it.copy(playing = true) }
        playJob = viewModelScope.launch {
            while (true) {
                delay(220)
                ui.update { s ->
                    val start = Timeline.tOf(if (s.showEarlier) Timeline.FIRST_YEAR else Timeline.RECENT_FROM, 0)
                    s.copy(t = if (s.t >= todayT) start else maxOf(s.t + 1, start))
                }
            }
        }
    }
    private fun stopPlaying() { playJob?.cancel(); playJob = null; ui.update { it.copy(playing = false) } }

    fun toggleDetail() = ui.update { it.copy(detailOn = !it.detailOn) }
    fun toggleLayer(id: String) = ui.update { it.copy(layersOn = it.layersOn + (id to !(it.layersOn[id] ?: false))) }
    fun setLayersOpen(open: Boolean) = ui.update { it.copy(layersOpen = open) }

    private val cameraState = MutableStateFlow(CameraView())
    /** The camera, kept apart from the screen state so map moves never recompose the panels. */
    val camera: StateFlow<CameraView> = cameraState.asStateFlow()
    fun onCamera(v: CameraView) {
        cameraState.value = v
        val d = v.zoom > 13.4
        if (ui.value.drilledFlag != d) ui.update { it.copy(drilledFlag = d) }
    }
    fun setSearchOpen(open: Boolean) = ui.update { it.copy(searchOpen = open, query = if (open) it.query else it.query) }
    fun map(cmd: MapCommand) { commands.trySend(cmd) }

    fun setLimit(acreFeetPerAcre: Double) {
        val id = ui.value.selectedId ?: return
        viewModelScope.launch { repository.setWaterLimit(id, ((acreFeetPerAcre * 10).roundToInt() / 10.0).coerceIn(0.5, 8.0)) }
    }

    fun retry() = reload.update { it + 1 }

    // ---------------- Compare and Print ----------------

    private val compareUi = MutableStateFlow(CompareUi())
    private val tuning = compareUi.map { Triple(it.weights, it.dP, it.dT) }.distinctUntilChanged()

    /** Priorities and what-ifs, re-scored 400 ms after the last change (POST /score with weights and scenario). */
    val compare: StateFlow<CompareUi> = combine(compareUi, field.map { it?.item?.id?.id to it?.limit }.distinctUntilChanged(), tuning) { ui, f, _ -> Triple(ui, f, ui.custom) }
        .flatMapLatest { (ui, f, custom) ->
            val (id, lim) = f
            if (!custom || id == null || lim == null) flowOf(ui.copy(rescored = null, busy = false))
            else kotlinx.coroutines.flow.flow { emit(ui.copy(busy = true)); kotlinx.coroutines.delay(400); emit(ui) }
                .flatMapLatest { u ->
                    if (u.busy) flowOf(u) else repository.score(id, lim, app.croplytics.domain.CompareLogic.requestWeights(u.weights), app.croplytics.data.remote.dto.ScenarioDto(u.dT, u.dP))
                        .map { s -> u.copy(rescored = s.dataOrNull, busy = s is LoadState.Loading || s is LoadState.Waking) }
                }
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), CompareUi())

    fun comparePick(id: String) = compareUi.update { it.copy(altId = id, table = false) }
    fun compareTable() = compareUi.update { it.copy(table = !it.table) }
    fun compareTune() = compareUi.update { it.copy(tune = !it.tune) }
    fun compareWeather(w: app.croplytics.domain.CompareLogic.Weather) = compareUi.update { it.copy(weather = w) }
    fun compareWeight(k: String, v: Int) = compareUi.update { it.copy(weights = it.weights + (k to v)) }
    fun compareRain(v: Double) = compareUi.update { it.copy(dP = v) }
    fun compareHeat(v: Double) = compareUi.update { it.copy(dT = v) }

    private val pick = MutableStateFlow<String?>(null)
    /** The option the adviser summary looks at. */
    val briefPick: StateFlow<String?> = pick.asStateFlow()
    fun pickBrief(id: String?) = pick.update { id }
    /** "Print this comparison for your adviser". */
    fun toBrief(id: String) { pick.update { id }; openTab(Tab.Print) }

    /** Opens a field section from a deep link (croplytics://field/<id>?tab=<0-4>) once the fields are in. */
    fun deepLink(id: String, tab: Int) {
        viewModelScope.launch {
            state.first { it.fields is LoadState.Ready }
            select(id)
            Tab.entries.getOrNull(tab)?.let { openTab(it) }
        }
    }

    companion object {
        /** Example water limit until the grower types theirs (PLAN.md 14 Nov): rice 5.0, forage 3.0 acre-ft/acre. */
        fun exampleLimit(item: FieldItem): Double = item.loc.water?.allocationInput?.value ?: if (item.id.family == "rice") 5.0 else 3.0
    }
}
