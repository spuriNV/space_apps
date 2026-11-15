import Foundation

/// Grower units first: acres, inches, acre-feet per acre, miles.
enum Units {
    static func acres(fromHectares ha: Double) -> Double { ha * 2.47105 }
    static func inches(fromMM mm: Double) -> Double { mm / 25.4 }
    /// Millimetres of water over a field = acre-feet per acre / 304.8.
    static func acreFeetPerAcre(fromMM mm: Double) -> Double { mm / 304.8 }

    /// "1.9" under 10, "12" above.
    static func inchesText(_ v: Double) -> String { v < 10 ? String(format: "%.1f", v) : String(Int(v.rounded())) }
    static func oneDecimal(_ v: Double) -> String { String(format: "%.1f", v) }

    static func ordinal(_ n: Int) -> String {
        let tens = n % 100
        let suffix: String
        if (11...13).contains(tens) { suffix = "th" } else {
            switch n % 10 {
            case 1: suffix = "st"
            case 2: suffix = "nd"
            case 3: suffix = "rd"
            default: suffix = "th"
            }
        }
        return "\(n)\(suffix)"
    }

    /// "2,243,711 acre-feet" -> "2.24 million acre-feet".
    static func acreFeetText(_ af: Double) -> String {
        if af >= 1_000_000 { return String(format: "%.2f million acre-feet", af / 1_000_000) }
        return "\(Int((af / 1000).rounded()).formatted()) thousand acre-feet"
    }

    /// "about 50 km (0.5 x 0.625 deg)" -> "about 31 miles"; "30 m" -> "100 ft". Pixel sizes become grower distances.
    static func distanceInGrowerUnits(_ raw: String) -> String {
        let pattern = #"(\d+(?:\.\d+)?)\s*(km|m)\b"#
        guard let re = try? NSRegularExpression(pattern: pattern),
              let match = re.firstMatch(in: raw, range: NSRange(raw.startIndex..., in: raw)),
              let numRange = Range(match.range(at: 1), in: raw),
              let unitRange = Range(match.range(at: 2), in: raw),
              let number = Double(raw[numRange]) else { return raw }
        let unit = raw[unitRange]
        let replacement: String
        if unit == "km" {
            let miles = number * 0.621
            replacement = miles < 10 ? String(format: "%.0f mile%@", max(miles, 1), miles >= 1.5 ? "s" : "") : "\(Int(miles.rounded())) miles"
        } else {
            let feet = number * 3.281
            replacement = feet >= 1000 ? String(format: "%.1f miles", feet / 5280) : "\(Int((feet / 10).rounded() * 10)) ft"
        }
        let full = Range(match.range, in: raw)!
        var out = raw
        out.replaceSubrange(full, with: replacement)
        // Drop the degree note in brackets: "(0.5 x 0.625 deg)".
        if let bracket = out.range(of: #"\s*\([^)]*deg[^)]*\)"#, options: .regularExpression) {
            out.removeSubrange(bracket)
        }
        return out
    }
}

/// Dates the way a grower says them: "13 Nov 2026", "mid Nov 2026".
enum GrowerDate {
    static let months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    static let monthsFull = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

    static var calendar: Calendar {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "America/Los_Angeles") ?? .current
        return c
    }

    /// Parses "2026-11-13" (or a longer ISO timestamp).
    static func parse(_ iso: String?) -> Date? {
        guard let iso, iso.count >= 10 else { return nil }
        let parts = iso.prefix(10).split(separator: "-").compactMap { Int($0) }
        guard parts.count == 3 else { return nil }
        return calendar.date(from: DateComponents(year: parts[0], month: parts[1], day: parts[2], hour: 12))
    }

    static func short(_ date: Date) -> String {
        let c = calendar.dateComponents([.year, .month, .day], from: date)
        return "\(c.day ?? 1) \(months[(c.month ?? 1) - 1]) \(c.year ?? 2026)"
    }

    static func short(_ iso: String?) -> String? { parse(iso).map(short) }

    static func shortNoYear(_ iso: String?) -> String? {
        guard let d = parse(iso) else { return nil }
        let c = calendar.dateComponents([.month, .day], from: d)
        return "\(c.day ?? 1) \(months[(c.month ?? 1) - 1])"
    }

    /// "early / mid / late Nov 2026" for a date.
    static func part(_ date: Date, withYear: Bool = true) -> String {
        let c = calendar.dateComponents([.year, .month, .day], from: date)
        let day = c.day ?? 1
        let part = day <= 10 ? "early" : day <= 20 ? "mid" : "late"
        return "\(part) \(months[(c.month ?? 1) - 1])" + (withYear ? " \(c.year ?? 2026)" : "")
    }

    /// "02-13" -> "mid Feb".
    static func monthDayPart(_ mmdd: String?) -> String? {
        guard let mmdd else { return nil }
        let p = mmdd.split(separator: "-").compactMap { Int($0) }
        guard p.count == 2, (1...12).contains(p[0]) else { return nil }
        return "\(p[1] <= 10 ? "early" : p[1] <= 20 ? "mid" : "late") \(months[p[0] - 1])"
    }

    static func year(_ date: Date) -> Int { calendar.component(.year, from: date) }

    /// 10-day step of the year (0...35) for a date: early / mid / late of each month.
    static func dekad(_ date: Date) -> Int {
        let c = calendar.dateComponents([.month, .day], from: date)
        let day = c.day ?? 1
        return ((c.month ?? 1) - 1) * 3 + (day <= 10 ? 0 : day <= 20 ? 1 : 2)
    }

    /// Long date for the summary page: "14 November 2026".
    static func long(_ date: Date) -> String {
        let c = calendar.dateComponents([.year, .month, .day], from: date)
        return "\(c.day ?? 1) \(monthsFull[(c.month ?? 1) - 1]) \(c.year ?? 2026)"
    }
}
