import Foundation
import Observation

@MainActor
@Observable
final class CompareViewModel {
    let field: FieldLocation
    private(set) var strategies: LoadState<[Strategy]> = .idle
    private(set) var calendar: LoadState<FieldCalendar> = .idle
    /// The engine's answer for the grower's limit (POST .../score); nil until re-scored.
    private(set) var scored: Fetched<[Strategy]>?
    private(set) var scoredLimit: Double?
    private(set) var isRescoring = false
    private(set) var rescoreError: AppError?
    private(set) var pendingRescore: Task<Void, Never>?

    private let repository: any FieldRepository
    private let limits: WaterLimitStore
    private let debounce: Duration

    init(field: FieldLocation, repository: any FieldRepository, limits: WaterLimitStore, debounce: Duration = .milliseconds(600)) {
        self.field = field
        self.repository = repository
        self.limits = limits
        self.debounce = debounce
    }

    var limit: WaterLimitStore.Limit { limits.limit(for: field.id) }

    /// The re-scored rotations when they match the current limit, else the stored scores.
    var current: [Strategy]? {
        if let scored, scoredLimit == limit.value { return scored.value }
        return strategies.value
    }

    var presentation: ComparePresentation? {
        guard let s = current, !s.isEmpty else { return nil }
        return CompareBuilder.build(strategies: s, calendar: calendar.value, limit: limit.value)
    }

    var isLoading: Bool { strategies.isLoading }
    var error: AppError? { strategies.error }
    var freshness: Freshness? {
        if let scored, scoredLimit == limit.value, let at = scored.savedAt { return Freshness(savedAt: at, refreshError: rescoreError) }
        return strategies.freshness?.savedAt != nil ? strategies.freshness : nil
    }

    func load() async {
        if strategies.value == nil { strategies = .loading }
        await withTaskGroup(of: Void.self) { group in
            group.addTask { await self.loadStrategies() }
            group.addTask { await self.loadCalendar() }
        }
        if !limit.isExample || scored == nil { await rescore() }
    }

    /// The grower changed the limit: save it for this field and re-score after a short pause.
    func setLimit(_ value: Double) {
        limits.set(value, for: field.id)
        scheduleRescore()
    }

    func resetLimit() {
        limits.reset(field.id)
        scheduleRescore()
    }

    private func scheduleRescore() {
        pendingRescore?.cancel()
        let delay = debounce
        pendingRescore = Task { [weak self] in
            try? await Task.sleep(for: delay)
            guard !Task.isCancelled else { return }
            await self?.rescore()
        }
    }

    func rescore() async {
        let value = limit.value
        isRescoring = true
        defer { isRescoring = false }
        do {
            let result = try await repository.score(fieldID: field.id, allocation: value)
            guard value == limit.value else { return } // the grower moved on
            scored = result
            scoredLimit = value
            rescoreError = nil
        } catch {
            rescoreError = AppError(error)
        }
    }

    private func loadStrategies() async { await consume(repository.strategies(field.id)) { self.strategies = $0 } }
    private func loadCalendar() async { await consume(repository.calendar(field.id)) { self.calendar = $0 } }
}
