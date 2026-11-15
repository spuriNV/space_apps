package app.croplytics.ui.summary

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.repository.FieldRepository
import app.croplytics.data.repository.LoadError
import app.croplytics.data.repository.LoadState
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.AdviserSummary
import app.croplytics.domain.AdviserSummaryBuilder
import app.croplytics.domain.ComingSeasonBuilder
import app.croplytics.domain.CompareBuilder
import app.croplytics.domain.FieldNames
import app.croplytics.domain.FieldNowBuilder
import app.croplytics.domain.OptionComparison
import app.croplytics.domain.WaterLimit
import app.croplytics.ui.common.combinedStatus
import app.croplytics.ui.common.fieldId
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import java.time.Clock
import java.time.Instant
import java.time.LocalDate
import javax.inject.Inject

data class SummaryUiState(
    val loading: Boolean = true,
    val waking: Boolean = false,
    val error: LoadError? = null,
    val offlineSavedAt: Instant? = null,
    val summary: AdviserSummary? = null,
    /** The top options the grower can choose to put on the page. */
    val choices: List<OptionComparison> = emptyList(),
    val chosenId: String? = null,
    /** Some parts (outlook, readings) are still loading; the page fills in as they arrive. */
    val partial: Boolean = false,
)

@OptIn(ExperimentalCoroutinesApi::class)
@HiltViewModel
class SummaryViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val repository: FieldRepository,
    private val clock: Clock,
) : ViewModel() {
    private val id = savedStateHandle.fieldId()
    private val reload = MutableStateFlow(0)
    private val chosen = MutableStateFlow<String?>(null)

    private val location = reload.flatMapLatest { repository.location(id, it > 0) }
    private val limit: Flow<Pair<Double?, Boolean>> = combine(repository.waterLimit(id), location) { saved, loc ->
        (saved ?: WaterLimit.example(loc.dataOrNull, id)) to (saved == null)
    }.distinctUntilChanged()

    /** Scored for the grower's limit, so the page matches Compare; plain strategies if there is no limit. */
    private val strategies: Flow<LoadState<List<StrategyDto>>> = limit.map { it.first }.distinctUntilChanged()
        .flatMapLatest { lim -> if (lim != null) repository.score(id, lim) else repository.strategies(id) }

    private val inputs = combine(
        reload.flatMapLatest { repository.calendar(id, it > 0) },
        reload.flatMapLatest { repository.nasaNow(id, it > 0) },
        reload.flatMapLatest { repository.outlook(id, it > 0) },
    ) { cal, now, outlook -> Triple(cal, now, outlook) }

    val state: StateFlow<SummaryUiState> = combine(location, strategies, limit, inputs, chosen) { loc, strat, (lim, example), (cal, now, outlook), pick ->
        val status = combinedStatus(loc, strat, cal, now, outlook)
        val l = loc.dataOrNull ?: return@combine SummaryUiState(
            loading = loc !is LoadState.Failed, waking = status.waking, error = (loc as? LoadState.Failed)?.error,
        )
        val today = LocalDate.now(clock)
        val identity = FieldNames.identity(l)
        val items = strat.dataOrNull
        val compare = items?.let { CompareBuilder.build(it, lim, identity.acres) }
        val choice = compare?.top?.firstOrNull { it.id == pick } ?: compare?.top?.firstOrNull()
        val nowSummary = FieldNowBuilder.build(l, cal.dataOrNull, now.dataOrNull, items, lim, example, today)
        val season = outlook.dataOrNull?.let { ComingSeasonBuilder.build(it, lim, example, CompareBuilder::shortName) }
        SummaryUiState(
            loading = false,
            waking = status.waking,
            offlineSavedAt = status.offlineSavedAt,
            summary = AdviserSummaryBuilder.build(identity, nowSummary, season, compare, choice, items, lim, example, today),
            choices = compare?.top.orEmpty(),
            chosenId = choice?.id,
            partial = listOf(strat, cal, now, outlook).any { it is LoadState.Loading || it is LoadState.Waking },
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), SummaryUiState())

    fun choose(optionId: String) = chosen.update { optionId }
    fun retry() = reload.update { it + 1 }
}
