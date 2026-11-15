import Foundation
import Observation

/// Whether any request is waiting on the sleeping free server. Drives the "Waking the server" banner.
@MainActor
@Observable
final class ServerStatus {
    private(set) var slowRequests: Set<UUID> = []
    var isWaking: Bool { !slowRequests.isEmpty }

    func handle(_ event: NetworkEvent) {
        switch event {
        case .slow(let id): slowRequests.insert(id)
        case .finished(let id): slowRequests.remove(id)
        }
    }

    /// A Sendable sink for `APIClient`, hopping to the main actor.
    nonisolated func sink() -> @Sendable (NetworkEvent) -> Void {
        { [weak self] event in
            Task { @MainActor in self?.handle(event) }
        }
    }
}
