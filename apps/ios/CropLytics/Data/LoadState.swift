import Foundation

/// A value with where it came from: live from the server, or the copy saved on a date.
struct Fetched<T: Sendable>: Sendable {
    var value: T
    /// nil when the value just came from the server.
    var savedAt: Date?
}

/// How fresh a shown value is.
struct Freshness: Equatable, Sendable {
    /// When the shown copy was saved; nil = live.
    var savedAt: Date?
    /// Set when a refresh failed and the saved copy is what is left.
    var refreshError: AppError?

    static let live = Freshness(savedAt: nil, refreshError: nil)
    var isLive: Bool { savedAt == nil }
}

/// The state of one piece of data on a screen.
enum LoadState<T: Sendable>: Sendable {
    case idle
    case loading
    case loaded(T, Freshness)
    case failed(AppError)

    var value: T? {
        if case .loaded(let v, _) = self { return v }
        return nil
    }

    var freshness: Freshness? {
        if case .loaded(_, let f) = self { return f }
        return nil
    }

    var error: AppError? {
        if case .failed(let e) = self { return e }
        return nil
    }

    var isLoading: Bool {
        switch self {
        case .idle, .loading: true
        default: false
        }
    }
}

/// Runs an offline-first stream into a state: the saved copy first, then the live answer.
/// If the refresh fails after a saved copy was shown, the saved copy stays with the error noted.
@MainActor
func consume<T: Sendable>(_ stream: AsyncThrowingStream<Fetched<T>, Error>, into assign: (LoadState<T>) -> Void) async {
    var last: Fetched<T>?
    do {
        for try await item in stream {
            last = item
            assign(.loaded(item.value, Freshness(savedAt: item.savedAt, refreshError: nil)))
        }
    } catch is CancellationError {
        return
    } catch {
        let appError = AppError(error)
        if let last {
            assign(.loaded(last.value, Freshness(savedAt: last.savedAt ?? .now, refreshError: appError)))
        } else {
            assign(.failed(appError))
        }
    }
}
