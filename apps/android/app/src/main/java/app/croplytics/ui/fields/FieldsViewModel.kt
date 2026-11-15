package app.croplytics.ui.fields

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.croplytics.data.repository.FieldRepository
import app.croplytics.data.repository.LoadError
import app.croplytics.data.repository.LoadState
import app.croplytics.domain.FieldIdentity
import app.croplytics.domain.FieldNames
import app.croplytics.domain.Rings
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

data class FieldRow(val identity: FieldIdentity, val rings: Rings)

data class FieldsUiState(
    val query: String = "",
    val rows: List<FieldRow> = emptyList(),
    val totalFields: Int = 0,
    val loading: Boolean = true,
    val waking: Boolean = false,
    val error: LoadError? = null,
    /** Set when the list comes from the phone because the server could not be reached. */
    val offlineSavedAt: Instant? = null,
    val refreshing: Boolean = false,
)

@HiltViewModel
class FieldsViewModel @Inject constructor(private val repository: FieldRepository) : ViewModel() {
    private val query = MutableStateFlow("")
    private val reload = MutableStateFlow(0)

    @OptIn(ExperimentalCoroutinesApi::class)
    private val locations = reload.flatMapLatest { n -> repository.locations(force = n > 0) }

    val state: StateFlow<FieldsUiState> = combine(locations, query) { load, q ->
        when (load) {
            LoadState.Loading -> FieldsUiState(query = q)
            LoadState.Waking -> FieldsUiState(query = q, waking = true)
            is LoadState.Failed -> FieldsUiState(query = q, loading = false, error = load.error)
            is LoadState.Ready -> {
                val all = load.data.map { FieldRow(FieldNames.identity(it), it.geometry?.rings().orEmpty()) }
                    .sortedWith(compareBy({ it.identity.county ?: "" }, { it.identity.name }))
                FieldsUiState(
                    query = q,
                    rows = filter(all, q),
                    totalFields = all.size,
                    loading = false,
                    offlineSavedAt = load.savedAt.takeIf { load.offline },
                    refreshing = load.refreshing,
                )
            }
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), FieldsUiState())

    fun onQueryChange(q: String) = query.update { q }
    fun retry() = reload.update { it + 1 }

    companion object {
        /** Every word must match the field's name, county, crop or state field number. */
        fun filter(rows: List<FieldRow>, q: String): List<FieldRow> {
            val words = q.lowercase().split(' ').filter(String::isNotBlank)
            if (words.isEmpty()) return rows
            return rows.filter { r -> words.all { it in r.identity.searchText } }
        }
    }
}
