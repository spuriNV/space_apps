import Foundation
import Observation

/// The grower's water limit per field (acre-feet per acre a year), kept on the device.
/// Until the grower sets one, an example limit is shown and labelled "example, change to yours"
/// (PLAN.md, 14 Nov: Colusa 5.0, Kings 3.0).
@MainActor
@Observable
final class WaterLimitStore {
    struct Limit: Equatable, Sendable {
        var value: Double
        var isExample: Bool
    }

    static let range: ClosedRange<Double> = 0.5...8.0
    private let defaults: UserDefaults
    private var stored: [String: Double]
    private static let key = "waterLimits.v1"

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        stored = (defaults.dictionary(forKey: Self.key) as? [String: Double]) ?? [:]
    }

    func limit(for fieldID: String) -> Limit {
        if let v = stored[fieldID] { return Limit(value: v, isExample: false) }
        return Limit(value: Self.example(for: fieldID), isExample: true)
    }

    func set(_ value: Double, for fieldID: String) {
        let clamped = min(max((value * 10).rounded() / 10, Self.range.lowerBound), Self.range.upperBound)
        stored[fieldID] = clamped
        defaults.set(stored, forKey: Self.key)
    }

    func reset(_ fieldID: String) {
        stored[fieldID] = nil
        defaults.set(stored, forKey: Self.key)
    }

    /// Example limits until the API sends one per field: rice ground 5.0, forage ground 3.0.
    static func example(for fieldID: String) -> Double {
        switch fieldID {
        case "car_colusa_rice": 5.0
        case "caf_tulare_forage": 3.0
        case let id where id.hasPrefix("car_"): 5.0
        case let id where id.hasPrefix("caf_"): 3.0
        default: 4.0
        }
    }
}
