package app.croplytics.ui.compare

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.repository.FieldRepository
import app.croplytics.data.repository.LoadError
import app.croplytics.data.repository.LoadState
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.CompareBuilder
import app.croplytics.domain.CompareSummary
import app.croplytics.domain.FieldNames
import app.croplytics.domain.WaterLimit
import app.croplytics.ui.common.combinedStatus
import app.croplytics.ui.common.fieldId
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.Instant
import javax.inject.Inject
import kotlin.math.roundToInt

/** One rotation's rule-of-thumb scores in the grower's words, for "More detail". */
data class ScoreRow(val name: String, val lines: List<String>)

data class CompareUiState(
    val loading: Boolean = true,
    val waking: Boolean = false,
    val error: LoadError? = null,
    val offlineSavedAt: Instant? = null,
    val limit: Double? = null,
    val limitIsExample: Boolean = true,
    val rescoring: Boolean = false,
    /** Re-scoring with the new limit failed; the ranking shown is the server's default. */
    val rescoreFailed: Boolean = false,
    val summary: CompareSummary? = null,
    val showAll: Boolean = false,
    val scoreRows: List<ScoreRow> = emptyList(),
)

@OptIn(ExperimentalCoroutinesApi::class, FlowPreview::class)
@HiltViewModel
class CompareViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val repository: FieldRepository,
) : ViewModel() {
    private val id = savedStateHandle.fieldId()
    private val reload = MutableStateFlow(0)
    /** The value under the grower's thumb, before it is saved. */
    private val draft = MutableStateFlow<Double?>(null)
    private val showAll = MutableStateFlow(false)
    private var persistJob: Job? = null

    private val location = reload.flatMapLatest { repository.location(id, it > 0) }
    private val strategies = reload.flatMapLatest { repository.strategies(id, it > 0) }

    private val limit: Flow<Pair<Double?, Boolean>> = combine(draft, repository.waterLimit(id), location) { d, saved, loc ->
        (d ?: saved ?: WaterLimit.example(loc.dataOrNull, id)) to (d == null && saved == null)
    }.distinctUntilChanged()

    /** Re-scored by the rotation engine (POST /score) each time the limit settles. */
    private val scored: Flow<Pair<Double?, LoadState<List<StrategyDto>>>> = limit.map { it.first }
        .debounce(450)
        .distinctUntilChanged()
        .flatMapLatest { lim -> if (lim == null) flowOf(null to LoadState.Loading) else repository.score(id, lim).map { lim to it } }

    val state: StateFlow<CompareUiState> = combine(location, strategies, limit, scored, showAll) { loc, base, (lim, example), (scoredFor, sc), all ->
        val status = combinedStatus(loc, base)
        val scoredItems = sc.dataOrNull
        val items = scoredItems ?: base.dataOrNull
        val acres = loc.dataOrNull?.let { FieldNames.identity(it).acres }
        when {
            items == null && base is LoadState.Failed -> CompareUiState(loading = false, error = base.error, limit = lim, limitIsExample = example)
            items == null -> CompareUiState(waking = status.waking || sc is LoadState.Waking, limit = lim, limitIsExample = example)
            else -> CompareUiState(
                loading = false,
                waking = status.waking,
                offlineSavedAt = status.offlineSavedAt,
                limit = lim,
                limitIsExample = example,
                rescoring = lim != null && (scoredFor != lim || sc is LoadState.Loading || sc is LoadState.Waking || (sc as? LoadState.Ready)?.refreshing == true),
                rescoreFailed = sc is LoadState.Failed,
                summary = CompareBuilder.build(items, lim, acres),
                showAll = all,
                scoreRows = scoreRows(items),
            )
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), CompareUiState())

    fun onLimitChange(acreFeetPerAcre: Double) {
        val v = ((acreFeetPerAcre * 10).roundToInt() / 10.0).coerceIn(WaterLimit.MIN, WaterLimit.MAX)
        draft.value = v
        persistJob?.cancel()
        persistJob = viewModelScope.launch {
            delay(400)
            repository.setWaterLimit(id, v)
        }
    }

    fun toggleShowAll() = showAll.update { !it }
    fun retry() = reload.update { it + 1 }

    private fun scoreRows(items: List<StrategyDto>): List<ScoreRow> {
        val labels = listOf(
            "water_use" to "Saves water", "erosion" to "Keeps soil in place", "organic_matter" to "Builds organic matter",
            "n_fixation" to "Adds nitrogen", "forage_value" to "Feed to cut or graze", "pest_break" to "Breaks pest cycles", "market" to "Easy to sell locally",
        )
        // scores that are the same for every rotation tell the grower nothing
        val varying = labels.filter { (k, _) -> items.mapNotNull { it.scores[k]?.usable }.distinct().size > 1 }
        return items.sortedByDescending { it.composite.value ?: 0.0 }.map { s ->
            ScoreRow(
                CompareBuilder.shortName(s.id, s.name) + if (s.isBaseline) " (today)" else "",
                varying.mapNotNull { (k, label) -> s.scores[k]?.usable?.let { "$label: ${it.roundToInt()} of 100" } } +
                    listOfNotNull(s.composite.value?.let { "Overall: ${it.roundToInt()} of 100" }),
            )
        }
    }
}
