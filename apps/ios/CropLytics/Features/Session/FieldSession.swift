import Foundation
import Observation

/// Everything the app knows about the open field, loaded once and shared by the map and every tab
/// (the web app's FieldBundle). Offline-first: each part shows its saved copy, then the live answer.
@MainActor
@Observable
final class FieldSession {
    private(set) var field: FieldLocation
    private(set) var nasaNow: LoadState<NasaNow> = .idle
    private(set) var calendar: LoadState<FieldCalendar> = .idle
    private(set) var strategies: LoadState<[Strategy]> = .idle
    private(set) var outlook: LoadState<Outlook> = .idle
    private(set) var daily: LoadState<DailyRecord> = .idle
    private(set) var calendarML: LoadState<MLCalendar> = .idle
    private(set) var models: LoadState<ModelReport> = .idle
    private(set) var stress: LoadState<StressReport> = .idle
    private(set) var waterSeen: LoadState<WaterSeen> = .idle
    private(set) var insurance: LoadState<InsuranceProfile> = .idle
    private(set) var firstNations: LoadState<FirstNationsDetail> = .idle
    private(set) var salmon: LoadState<SalmonInfo> = .idle
    private(set) var iss: LoadState<ISSPhotos> = .idle
    private(set) var grid: LoadState<FieldGrid> = .idle
    private(set) var reserves: LoadState<ReserveOutlines> = .idle

    private let repository: any FieldRepository

    init(field: FieldLocation, repository: any FieldRepository) {
        self.field = field
        self.repository = repository
    }

    /// A newer copy of the field from the list (the saved copy may predate fields the API added).
    func update(field new: FieldLocation) { if new.id == field.id { field = new } }

    /// Loads the parts the first screens need, then the rest.
    func load(force: Bool = false) async {
        if let running = loadTask, !force { await running.value; return }
        let task = Task { await self.loadAll() }
        loadTask = task
        await task.value
    }
    private var loadTask: Task<Void, Never>?

    private func loadAll() async {
        if nasaNow.value == nil { nasaNow = .loading }
        if calendar.value == nil { calendar = .loading }
        if strategies.value == nil { strategies = .loading }
        if outlook.value == nil { outlook = .loading }
        if daily.value == nil { daily = .loading }
        await withTaskGroup(of: Void.self) { group in
            group.addTask { await self.loadNasaNow() }
            group.addTask { await self.loadCalendar() }
            group.addTask { await self.loadStrategies() }
            group.addTask { await self.loadOutlook() }
            group.addTask { await self.loadDaily() }
            group.addTask { await self.loadExtras() }
        }
    }

    /// The 30 m grid for the 3D view: loaded when the grower opens it.
    func loadGrid() async {
        guard grid.value == nil, !grid.isLoadingNow else { return }
        grid = .loading
        await consume(repository.grid(field.id)) { self.grid = $0 }
    }

    /// Reserve outlines near a BC field, for the map layer.
    func loadReserves() async {
        guard field.isBC, reserves.value == nil, !reserves.isLoadingNow else { return }
        reserves = .loading
        await consume(repository.reserves(field.id)) { self.reserves = $0 }
    }

    /// The rotations re-scored by the engine for the grower's settings (Compare) replace the stored ones everywhere.
    func apply(scored: [Strategy]) {
        let keepOpenET = Dictionary((strategies.value ?? []).map { ($0.id, $0.water.etcVsOpenetPct) }, uniquingKeysWith: { a, _ in a })
        let merged = scored.map { s -> Strategy in
            guard s.water.etcVsOpenetPct == nil, let o = keepOpenET[s.id] ?? nil else { return s }
            var m = s
            m = Strategy(id: s.id, name: s.name, isBaseline: s.isBaseline, cycleYears: s.cycleYears, calendar: s.calendar,
                         water: .init(irrigationNeedMm: s.water.irrigationNeedMm, etcVsOpenetPct: o, allocationStatus: s.water.allocationStatus),
                         exposure: s.exposure, scores: s.scores, composite: s.composite, brief: s.brief, filteredOut: s.filteredOut)
            m.shortName = s.shortName
            return m
        }
        scoredStrategies = merged
    }
    private(set) var scoredStrategies: [Strategy]?
    /// The rotations to show: re-scored when available.
    var currentStrategies: [Strategy]? { scoredStrategies ?? strategies.value }

    /// The oldest saved copy on screen, for the "saved on" note.
    var freshness: Freshness? {
        [nasaNow.freshness, calendar.freshness, strategies.freshness, outlook.freshness].compactMap { $0 }
            .filter { $0.savedAt != nil }
            .min { ($0.savedAt ?? .distantFuture) < ($1.savedAt ?? .distantFuture) }
    }

    /// Nothing at all could be loaded.
    var blockingError: AppError? {
        guard let e = calendar.error, nasaNow.error != nil, strategies.error != nil else { return nil }
        return e
    }

    var isLoadingCore: Bool { calendar.isLoading && nasaNow.isLoading }

    // MARK: Compare: priorities, what-ifs and re-scoring (POST .../score)

    static let priorityKeys: [(key: String, label: String)] = [
        ("water_use", "Saving water"), ("forage_value", "Feed to cut or graze"), ("n_fixation", "Adding nitrogen"),
        ("erosion", "Keeping soil in place"), ("organic_matter", "Building organic matter"), ("pest_break", "Breaking pest cycles"),
    ]
    static func defaultWeight(_ key: String) -> Int { key == "pest_break" ? 0 : 1 }

    var weights: [String: Int] = [:] { didSet { if weights != oldValue { scheduleRescore() } } }
    var scenario = ScoreRequest.Scenario(dT_c: 0, dP_pct: 0) { didSet { if scenario != oldValue { scheduleRescore() } } }
    var weather: CompareBuilder.Weather = .typical
    private(set) var isRescoring = false
    private(set) var rescoreError: AppError?
    private(set) var scoredFreshness: Freshness?
    private(set) var pendingRescore: Task<Void, Never>?
    /// The current water limit, for re-scoring; set by the screens from the limit store.
    var limitForScoring: Double = 0
    var rescoreDebounce: Duration = .milliseconds(450)

    var isCustomScoring: Bool { !weights.isEmpty || scenario.dT_c != 0 || scenario.dP_pct != 0 }

    func weight(_ key: String) -> Int { weights[key] ?? Self.defaultWeight(key) }

    func scoreRequest(limit: Double) -> ScoreRequest {
        guard isCustomScoring else { return ScoreRequest(allocation: limit) }
        var w = Dictionary(uniqueKeysWithValues: Self.priorityKeys.map { ($0.key, weight($0.key)) })
        w["market"] = 0
        return ScoreRequest(allocation: limit, weights: w, scenario: scenario)
    }

    func scheduleRescore(limit: Double? = nil) {
        if let limit { limitForScoring = limit }
        pendingRescore?.cancel()
        let delay = rescoreDebounce
        pendingRescore = Task { [weak self] in
            try? await Task.sleep(for: delay)
            guard !Task.isCancelled else { return }
            await self?.rescore()
        }
    }

    func rescore() async {
        let request = scoreRequest(limit: limitForScoring)
        isRescoring = true
        defer { isRescoring = false }
        do {
            let r = try await repository.score(fieldID: field.id, request: request)
            guard request == scoreRequest(limit: limitForScoring) else { return } // the grower moved on
            apply(scored: r.value)
            scoredFreshness = r.savedAt.map { Freshness(savedAt: $0, refreshError: nil) }
            rescoreError = nil
        } catch {
            rescoreError = AppError(error)
        }
    }

    // MARK: Loaders

    private func loadNasaNow() async { await consume(repository.nasaNow(field.id)) { self.nasaNow = $0 } }
    private func loadStrategies() async { await consume(repository.strategies(field.id)) { self.strategies = $0 } }
    private func loadOutlook() async { await consume(repository.outlook(field.id)) { self.outlook = $0 } }
    private func loadDaily() async { await consume(repository.daily(field.id)) { self.daily = $0 } }
    private func loadCalendar() async {
        await consume(repository.calendar(field.id)) { self.calendar = $0 }
        // Fall back to the Sentinel-2 / Landsat calendar when the NASA HLS one isn't served.
        if case .failed(.notFound) = calendar {
            await consume(repository.stream(.calendar(field.id, hls: false), as: FieldCalendar.self)) { self.calendar = $0 }
        }
    }

    private func loadExtras() async {
        calendarML = .loading; models = .loading; stress = .loading; waterSeen = .loading; insurance = .loading; iss = .loading
        if field.isBC { firstNations = .loading; salmon = .loading }
        await withTaskGroup(of: Void.self) { group in
            group.addTask { await self.loadML() }
            group.addTask { await self.loadModels() }
            group.addTask { await self.loadStress() }
            group.addTask { await self.loadWater() }
            group.addTask { await self.loadInsurance() }
            group.addTask { await self.loadISS() }
            if field.isBC {
                group.addTask { await self.loadFirstNations() }
                group.addTask { await self.loadSalmon() }
            }
        }
    }
    private func loadML() async { await consume(repository.calendarML(field.id)) { self.calendarML = $0 } }
    private func loadModels() async { await consume(repository.models(field.id)) { self.models = $0 } }
    private func loadStress() async { await consume(repository.stress(field.id)) { self.stress = $0 } }
    private func loadWater() async { await consume(repository.waterSeen(field.id)) { self.waterSeen = $0 } }
    private func loadInsurance() async { await consume(repository.insurance(field.id)) { self.insurance = $0 } }
    private func loadISS() async { await consume(repository.iss(field.id)) { self.iss = $0 } }
    private func loadFirstNations() async { await consume(repository.firstNations(field.id)) { self.firstNations = $0 } }
    private func loadSalmon() async { await consume(repository.salmon(field.id)) { self.salmon = $0 } }
}

extension LoadState {
    /// True only while a request is running (not idle).
    var isLoadingNow: Bool { if case .loading = self { return true }; return false }
}
