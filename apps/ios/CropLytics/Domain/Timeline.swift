import Foundation

/// A point on the field's timeline: one 10-day step (early, mid or late in a month), as in the web app's `t`.
/// The app views "today" by default; the date control and replay move it.
struct TimePoint: Hashable, Comparable, Sendable {
    static let firstYear = 2016
    /// (year - 2016) * 36 + dekad
    let index: Int

    init(index: Int) { self.index = max(0, index) }
    init(year: Int, dekad: Int) { self.init(index: (year - Self.firstYear) * 36 + min(max(dekad, 0), 35)) }
    init(date: Date) { self.init(year: GrowerDate.year(date), dekad: GrowerDate.dekad(date)) }
    init?(iso: String) {
        guard let d = GrowerDate.parse(iso) else { return nil }
        self.init(date: d)
    }

    var year: Int { Self.firstYear + index / 36 }
    var dekad: Int { index % 36 }
    var month: Int { dekad / 3 + 1 }

    /// The middle day of the step, for date-based readings.
    var date: Date {
        GrowerDate.calendar.date(from: DateComponents(year: year, month: month, day: [5, 15, 25][dekad % 3], hour: 12)) ?? .now
    }
    /// The last day of the step ("so far" cut-off).
    var endDate: Date {
        let day = dekad % 3 == 0 ? 10 : dekad % 3 == 1 ? 20 : (GrowerDate.calendar.range(of: .day, in: .month, for: date)?.count ?? 30)
        return GrowerDate.calendar.date(from: DateComponents(year: year, month: month, day: day, hour: 12)) ?? date
    }
    var iso: String { String(format: "%04d-%02d-%02d", year, month, [5, 15, 25][dekad % 3]) }

    /// "mid Nov 2026"
    var label: String { "\(dekadText(dekad)) \(year)" }

    static func < (a: TimePoint, b: TimePoint) -> Bool { a.index < b.index }
    func advanced(by n: Int) -> TimePoint { TimePoint(index: index + n) }
}

/// The date control's quick picks, in the grower's words, relative to today.
enum QuickDates {
    static func picks(today: TimePoint) -> [(label: String, sub: String, t: TimePoint)] {
        let y = today.year
        let summerYear = today.month >= 9 ? y : y - 1
        let springYear = today.month >= 6 ? y : y - 1
        let summer = TimePoint(year: summerYear, dekad: 19), spring = TimePoint(year: springYear, dekad: 10)
        return [
            ("Today", today.label, today),
            ("Last summer", "Jul \(summerYear)", summer),
            ("Last spring", "Apr \(springYear)", spring),
            ("2023 floods", "Mar 2023", TimePoint(year: 2023, dekad: 7)),
            ("2022 drought", "Jul 2022", TimePoint(year: 2022, dekad: 19)),
        ]
    }

    /// Years in the month picker: the last 4 by default (PLAN.md), from 2016 with "Show earlier years".
    static func years(today: TimePoint, earlier: Bool) -> [Int] {
        Array((earlier ? TimePoint.firstYear : today.year - 3)...today.year).reversed()
    }
}
