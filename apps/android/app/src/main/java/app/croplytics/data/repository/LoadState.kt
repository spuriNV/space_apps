package app.croplytics.data.repository

import java.time.Instant

/** What a screen knows about one piece of data. */
sealed interface LoadState<out T> {
    /** Nothing yet; show a skeleton. */
    data object Loading : LoadState<Nothing>

    /** Nothing yet and the request is slow: the free server is waking up (up to a minute). */
    data object Waking : LoadState<Nothing>

    /**
     * Data to show. [savedAt] is when it came from the server. [offline] means the latest request
     * failed and this is the copy saved on the phone; [refreshing] means a newer copy is on its way.
     */
    data class Ready<T>(
        val data: T,
        val savedAt: Instant,
        val offline: Boolean = false,
        val refreshing: Boolean = false,
    ) : LoadState<T>

    data class Failed(val error: LoadError) : LoadState<Nothing>
}

enum class LoadError {
    /** No connection and nothing saved. */
    NoConnection,

    /** The server answered, but this part does not exist for this field yet (HTTP 404). */
    NotAvailable,

    /** The server failed or timed out. */
    Server,
}

val <T> LoadState<T>.dataOrNull: T? get() = (this as? LoadState.Ready<T>)?.data

inline fun <T, R> LoadState<T>.map(f: (T) -> R): LoadState<R> = when (this) {
    is LoadState.Ready -> LoadState.Ready(f(data), savedAt, offline, refreshing)
    LoadState.Loading -> LoadState.Loading
    LoadState.Waking -> LoadState.Waking
    is LoadState.Failed -> this
}
