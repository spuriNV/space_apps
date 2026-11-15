import Foundation

/// One question a grower would ask and a plain answer, with one small source line.
struct Answer: Identifiable, Sendable, Equatable {
    enum Tone: Sendable { case normal, warn }
    let id: String
    let question: String
    let headline: String
    let detail: String
    let cite: String
    var tone: Tone = .normal
}

/// A single reading with a reference mark (normal, limit, full canopy).
struct Meter: Sendable, Equatable {
    let label: String
    let valueText: String
    let value: Double
    let reference: Double?
    let referenceLabel: String
    let scaleMax: Double
    let note: String
    var warn: Bool = false
    /// VoiceOver sentence for the whole reading.
    var accessibilityText: String { "\(label): \(valueText). \(note)" }
}

/// A value with its likely range.
struct NumRange: Sendable, Equatable {
    var value: Double
    var low: Double
    var high: Double

    init(_ value: Double, low: Double? = nil, high: Double? = nil) {
        self.value = value
        self.low = low ?? value
        self.high = high ?? value
    }

    init?(_ n: SourcedNumber?) {
        guard let n, let v = n.value else { return nil }
        self.init(v, low: n.low, high: n.high)
    }

    func map(_ f: (Double) -> Double) -> NumRange { NumRange(f(value), low: f(low), high: f(high)) }
    var hasSpread: Bool { abs(high - low) > 0.05 }
}
