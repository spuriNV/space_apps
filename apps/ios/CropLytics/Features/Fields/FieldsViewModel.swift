import Foundation
import Observation

/// One row of the pick list, in the grower's words.
struct FieldRow: Identifiable, Sendable, Equatable {
    let id: String
    let name: String
    let county: String
    let acres: Int
    let crop: String
    let record: String

    init(_ f: FieldLocation) {
        id = f.id
        name = FieldNaming.displayName(f)
        county = FieldNaming.county(f)
        acres = FieldNaming.acres(f)
        crop = FieldNaming.cropLine(f)
        record = FieldNaming.recordLine(f)
    }

    var accessibilityText: String { "\(name). \(acres) acres, \(county) County. \(crop)." }
}

/// The searchable field list. Data comes from `AppModel` (shared with the field tabs).
@MainActor
@Observable
final class FieldsViewModel {
    var searchText = ""
    private let app: AppModel

    init(app: AppModel) {
        self.app = app
    }

    var state: LoadState<[FieldLocation]> { app.fields }

    var rows: [FieldRow] {
        let all = (app.fields.value ?? []).map(FieldRow.init)
        return Self.filter(all, query: searchText)
    }

    /// Matches name, county, crop or town, ignoring case and accents; every word must match.
    static func filter(_ rows: [FieldRow], query: String) -> [FieldRow] {
        let words = query.split(whereSeparator: \.isWhitespace).map { String($0) }
        guard !words.isEmpty else { return rows }
        return rows.filter { row in
            let hay = "\(row.name) \(row.county) County \(row.crop) \(row.acres) acres"
            return words.allSatisfy { hay.range(of: $0, options: [.caseInsensitive, .diacriticInsensitive]) != nil }
        }
    }

    func refresh() async { await app.loadFields() }
    func open(_ id: String) { app.open(id) }
}
