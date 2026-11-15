package app.croplytics.ui.common

import androidx.lifecycle.SavedStateHandle
import app.croplytics.data.remote.dto.GlossaryItemDto
import app.croplytics.data.repository.LoadError
import app.croplytics.data.repository.LoadState
import java.time.Instant

/** The field id every field screen is opened with (navigation argument `id`). */
fun SavedStateHandle.fieldId(): String = checkNotNull(get<String>("id")) { "Field screens need an id" }

/** A "More detail" part: still loading, not available (with why), or lines to show. */
sealed interface DetailPart {
    data object Loading : DetailPart
    data class Unavailable(val reason: String) : DetailPart
    data class Lines(val lines: List<String>) : DetailPart
}

fun <T> LoadState<T>.toDetail(build: (T) -> List<String>): DetailPart = when (this) {
    LoadState.Loading, LoadState.Waking -> DetailPart.Loading
    is LoadState.Ready -> DetailPart.Lines(build(data))
    is LoadState.Failed -> DetailPart.Unavailable(
        when (error) {
            LoadError.NotAvailable -> "Not on the server for this field yet."
            LoadError.NoConnection -> "Offline, and not saved on this phone yet."
            LoadError.Server -> "The server didn't answer; try again later."
        },
    )
}

/** Overall status of several loads: any still waking the server, and the oldest offline copy shown. */
data class CombinedStatus(val waking: Boolean, val offlineSavedAt: Instant?)

fun combinedStatus(vararg states: LoadState<*>): CombinedStatus = CombinedStatus(
    waking = states.any { it is LoadState.Waking },
    offlineSavedAt = states.filterIsInstance<LoadState.Ready<*>>().filter { it.offline }.minOfOrNull { it.savedAt },
)

fun glossaryLookup(items: List<GlossaryItemDto>, ids: List<String>): GlossaryItemDto? =
    ids.firstNotNullOfOrNull { id -> items.firstOrNull { it.id == id } }
