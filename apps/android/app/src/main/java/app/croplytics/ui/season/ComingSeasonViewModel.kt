package app.croplytics.ui.season

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.croplytics.data.repository.FieldRepository
import app.croplytics.data.repository.LoadError
import app.croplytics.data.repository.LoadState
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.ComingSeasonBuilder
import app.croplytics.domain.ComingSeasonSummary
import app.croplytics.domain.CompareBuilder
import app.croplytics.domain.WaterLimit
import app.croplytics.ui.common.combinedStatus
import app.croplytics.ui.common.fieldId
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import java.time.Instant
import javax.inject.Inject

data class ComingSeasonUiState(
    val loading: Boolean = true,
    val waking: Boolean = false,
    val error: LoadError? = null,
    val offlineSavedAt: Instant? = null,
    val summary: ComingSeasonSummary? = null,
)

@OptIn(ExperimentalCoroutinesApi::class)
@HiltViewModel
class ComingSeasonViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val repository: FieldRepository,
) : ViewModel() {
    private val id = savedStateHandle.fieldId()
    private val reload = MutableStateFlow(0)

    val state: StateFlow<ComingSeasonUiState> = combine(
        reload.flatMapLatest { repository.outlook(id, it > 0) },
        reload.flatMapLatest { repository.location(id, it > 0) },
        repository.waterLimit(id),
    ) { outlook, loc, saved ->
        val status = combinedStatus(outlook, loc)
        val o = outlook.dataOrNull
        when {
            o != null -> {
                val limit = saved ?: WaterLimit.example(loc.dataOrNull, id)
                ComingSeasonUiState(
                    loading = false,
                    waking = status.waking,
                    offlineSavedAt = status.offlineSavedAt,
                    summary = ComingSeasonBuilder.build(o, limit, saved == null, CompareBuilder::shortName),
                )
            }
            outlook is LoadState.Failed -> ComingSeasonUiState(loading = false, error = outlook.error)
            else -> ComingSeasonUiState(waking = status.waking)
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), ComingSeasonUiState())

    fun retry() = reload.update { it + 1 }
}
