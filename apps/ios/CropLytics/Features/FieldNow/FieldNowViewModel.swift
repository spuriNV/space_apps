import Foundation
import Observation

@MainActor
@Observable
final class FieldNowViewModel {
    let field: FieldLocation
    private(set) var nasaNow: LoadState<NasaNow> = .idle
    private(set) var calendar: LoadState<FieldCalendar> = .idle
    private(set) var strategies: LoadState<[Strategy]> = .idle

    private let repository: any FieldRepository
    private let limits: WaterLimitStore
    private let today: Date

    init(field: FieldLocation, repository: any FieldRepository, limits: WaterLimitStore, today: Date) {
        self.field = field
        self.repository = repository
        self.limits = limits
        self.today = today
    }

    var limit: WaterLimitStore.Limit { limits.limit(for: field.id) }

    var presentation: FieldNowPresentation {
        FieldNowBuilder.build(.init(field: field, nasaNow: nasaNow.value, calendar: calendar.value,
                                    strategies: strategies.value, limit: limit, today: today))
    }

    /// Placeholders until the readings behind the summary have answered.
    var isLoading: Bool { nasaNow.isLoading || calendar.isLoading }

    /// An error screen only when nothing at all could be loaded.
    var blockingError: AppError? {
        guard let e = nasaNow.error, calendar.error != nil, strategies.error != nil else { return nil }
        return e
    }

    /// The oldest saved copy on screen, for the "saved on" note.
    var freshness: Freshness? {
        [nasaNow.freshness, calendar.freshness, strategies.freshness].compactMap { $0 }
            .filter { $0.savedAt != nil }
            .min { ($0.savedAt ?? .distantFuture) < ($1.savedAt ?? .distantFuture) }
    }

    func load() async {
        if nasaNow.value == nil { nasaNow = .loading }
        if calendar.value == nil { calendar = .loading }
        if strategies.value == nil { strategies = .loading }
        await withTaskGroup(of: Void.self) { group in
            group.addTask { await self.loadNasaNow() }
            group.addTask { await self.loadCalendar() }
            group.addTask { await self.loadStrategies() }
        }
    }

    private func loadNasaNow() async { await consume(repository.nasaNow(field.id)) { self.nasaNow = $0 } }
    private func loadStrategies() async { await consume(repository.strategies(field.id)) { self.strategies = $0 } }
    private func loadCalendar() async {
        await consume(repository.calendar(field.id)) { self.calendar = $0 }
        // Fall back to the Sentinel-2 / Landsat calendar when the NASA HLS one isn't served.
        if case .failed(.notFound) = calendar {
            await consume(repository.stream(.calendar(field.id, hls: false), as: FieldCalendar.self)) { self.calendar = $0 }
        }
    }
}
