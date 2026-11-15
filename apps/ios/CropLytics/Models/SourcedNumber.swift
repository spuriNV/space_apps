import Foundation

/// A number with its likely range (schemas/sourced_number.schema.json).
/// Decodes either the full object `{value, low, high, unit, note}` or a bare number, because some routes send plain numbers.
struct SourcedNumber: Codable, Sendable, Equatable {
    var value: Double?
    var low: Double?
    var high: Double?
    var unit: String?
    var note: String?

    init(value: Double?, low: Double? = nil, high: Double? = nil, unit: String? = nil, note: String? = nil) {
        self.value = value
        self.low = low
        self.high = high
        self.unit = unit
        self.note = note
    }

    private enum CodingKeys: String, CodingKey { case value, low, high, unit, note }

    init(from decoder: Decoder) throws {
        if let single = try? decoder.singleValueContainer(), let number = try? single.decode(Double.self) {
            self.init(value: number)
            return
        }
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.init(
            value: try c.decodeIfPresent(LossyDouble.self, forKey: .value)?.value,
            low: try c.decodeIfPresent(LossyDouble.self, forKey: .low)?.value,
            high: try c.decodeIfPresent(LossyDouble.self, forKey: .high)?.value,
            unit: try? c.decodeIfPresent(String.self, forKey: .unit),
            note: try? c.decodeIfPresent(String.self, forKey: .note)
        )
    }

    /// Low end, falling back to the value.
    var lo: Double? { low ?? value }
    /// High end, falling back to the value.
    var hi: Double? { high ?? value }
}

/// A Double that tolerates `null`, strings and integers.
struct LossyDouble: Decodable, Sendable {
    let value: Double?
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { value = nil }
        else if let d = try? c.decode(Double.self) { value = d }
        else if let s = try? c.decode(String.self) { value = Double(s) }
        else { value = nil }
    }
}

/// A String that tolerates numbers (some IDs come back as numbers).
struct LossyString: Decodable, Sendable {
    let value: String?
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { value = nil }
        else if let s = try? c.decode(String.self) { value = s }
        else if let i = try? c.decode(Int.self) { value = String(i) }
        else if let d = try? c.decode(Double.self) { value = String(d) }
        else { value = nil }
    }
}
