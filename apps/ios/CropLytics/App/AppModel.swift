import Foundation
import Observation

enum AppTab: String, Hashable, CaseIterable, Sendable {
    case fields, now, season, compare, summary

    var title: String {
        switch self {
        case .fields: "Fields"
        case .now: "Field now"
        case .season: "Coming season"
        case .compare: "Compare"
        case .summary: "Summary"
        }
    }

    var symbol: String {
        switch self {
        case .fields: "square.grid.2x2"
        case .now: "leaf"
        case .season: "cloud.sun.rain"
        case .compare: "arrow.left.arrow.right"
        case .summary: "doc.text"
        }
    }
}

/// App-wide state: the list of fields, which one is open and which tab is showing.
@MainActor
@Observable
final class AppModel {
    var tab: AppTab
    private(set) var selectedFieldID: String?
    private(set) var fields: LoadState<[FieldLocation]> = .idle

    private let repository: any FieldRepository
    private let defaults: UserDefaults
    private static let lastFieldKey = "lastFieldID"

    init(repository: any FieldRepository, defaults: UserDefaults = .standard, initialTab: AppTab? = nil, initialField: String? = nil) {
        self.repository = repository
        self.defaults = defaults
        selectedFieldID = initialField ?? defaults.string(forKey: Self.lastFieldKey)
        tab = initialTab ?? .fields
    }

    var selectedField: FieldLocation? {
        guard let id = selectedFieldID else { return nil }
        return fields.value?.first { $0.id == id }
    }

    func loadFields() async {
        if fields.value == nil { fields = .loading }
        await consume(repository.locations()) { self.fields = $0 }
    }

    /// Opens a field on "Field now".
    func open(_ fieldID: String) {
        select(fieldID)
        tab = .now
    }

    func select(_ fieldID: String) {
        selectedFieldID = fieldID
        defaults.set(fieldID, forKey: Self.lastFieldKey)
    }
}
