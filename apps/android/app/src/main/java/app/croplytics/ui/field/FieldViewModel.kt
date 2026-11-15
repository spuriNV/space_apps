package app.croplytics.ui.field

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.croplytics.data.repository.FieldRepository
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.FieldIdentity
import app.croplytics.domain.FieldNames
import app.croplytics.domain.Rings
import app.croplytics.ui.common.fieldId
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import javax.inject.Inject

data class FieldHeader(val identity: FieldIdentity? = null, val rings: Rings = emptyList())

/** Field name and outline for the top bar and the map; the tabs load their own data. */
@HiltViewModel
class FieldViewModel @Inject constructor(savedStateHandle: SavedStateHandle, repository: FieldRepository) : ViewModel() {
    val fieldId = savedStateHandle.fieldId()
    val header: StateFlow<FieldHeader> = repository.location(fieldId)
        .map { s -> s.dataOrNull?.let { FieldHeader(FieldNames.identity(it), it.geometry?.rings().orEmpty()) } ?: FieldHeader() }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), FieldHeader())
}
