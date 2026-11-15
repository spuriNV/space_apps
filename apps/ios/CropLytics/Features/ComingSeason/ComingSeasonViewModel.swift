import Foundation
import Observation

@MainActor
@Observable
final class ComingSeasonViewModel {
    let field: FieldLocation
    private(set) var outlook: LoadState<Outlook> = .idle
    private(set) var nasaNow: LoadState<NasaNow> = .idle
    private(set) var strategies: LoadState<[Strategy]> = .idle
    private let repository: any FieldRepository
    private let limits: WaterLimitStore

    init(field: FieldLocation, repository: any FieldRepository, limits: WaterLimitStore) {
        self.field = field
        self.repository = repository
        self.limits = limits
    }

    var presentation: ComingSeasonPresentation? {
        guard let o = outlook.value else { return nil }
        return ComingSeasonBuilder.build(outlook: o, field: field, nasaNow: nasaNow.value, strategies: strategies.value,
                                         limit: limits.limit(for: field.id))
    }

    var isLoading: Bool { outlook.isLoading }
    var error: AppError? { outlook.error }
    var freshness: Freshness? { outlook.freshness?.savedAt != nil ? outlook.freshness : nil }

    func load() async {
        if outlook.value == nil { outlook = .loading }
        await withTaskGroup(of: Void.self) { group in
            group.addTask { await self.loadOutlook() }
            group.addTask { await self.loadNasaNow() }
            group.addTask { await self.loadStrategies() }
        }
    }

    private func loadOutlook() async { await consume(repository.outlook(field.id)) { self.outlook = $0 } }
    private func loadNasaNow() async { await consume(repository.nasaNow(field.id)) { self.nasaNow = $0 } }
    private func loadStrategies() async { await consume(repository.strategies(field.id)) { self.strategies = $0 } }
}
