import Foundation

/// What the satellites saw on the field in one 10-day step.
enum CoverClass: String, Sendable, CaseIterable {
    case bare = "b", partial = "p", covered = "c", water = "w", noView = "u"

    init(apiClass: String?) {
        switch apiClass {
        case "bare": self = .bare
        case "partial": self = .partial
        case "covered": self = .covered
        case "water": self = .water
        default: self = .noView
        }
    }

    var label: String {
        switch self {
        case .bare: "Bare"
        case .partial: "Thin cover"
        case .covered: "Green cover"
        case .water: "Under water"
        case .noView: "No clear view"
        }
    }
}

/// Bare = satellite greenness below 0.2 and not under water (frontend/app/src/bare.ts). One definition everywhere.
let bareDefinition = "Bare = satellite greenness below 0.2 and not under water."

extension FieldCalendar {
    func year(_ y: Int) -> Year? { years.first { $0.year == y } }

    /// 36 ten-day classes for a year (early/mid/late of each month), from the calendar's segments.
    func classes(for y: Int) -> [CoverClass] {
        guard let year = year(y) else { return Array(repeating: .noView, count: 36) }
        let cal = GrowerDate.calendar
        return (0..<36).map { k in
            let month = k / 3 + 1, day = [5, 15, 25][k % 3]
            guard let date = cal.date(from: DateComponents(year: y, month: month, day: day)),
                  let doy = cal.ordinality(of: .day, in: .year, for: date) else { return .noView }
            let seg = year.segments.first { doy >= $0.startDoy && doy <= $0.endDoy }
            return CoverClass(apiClass: seg?.cls)
        }
    }

    /// The newest observation with a greenness value, at or before `date`.
    func latestObservation(before date: Date) -> (date: Date, ndvi: Double?, cls: CoverClass)? {
        let all = years.sorted { $0.year > $1.year }.flatMap { $0.observations.reversed() }
        for o in all {
            guard let d = GrowerDate.parse(o.date), d <= date else { continue }
            return (d, o.ndvi, CoverClass(apiClass: o.cls))
        }
        return nil
    }

    /// The year of the last processed observation.
    var lastYear: Int? {
        if let d = GrowerDate.parse(lastObservation) { return GrowerDate.year(d) }
        return years.filter { !$0.segments.isEmpty }.map(\.year).max()
    }

    /// Bare days in one year, scaled up for the steps with no clear view. nil when under half the year was seen.
    func bareDays(in y: Int) -> Int? {
        let steps = classes(for: y)
        let clear = steps.filter { $0 != .noView }.count
        guard clear >= 18 else { return nil }
        return Int((Double(steps.filter { $0 == .bare }.count) / Double(clear) * 365).rounded())
    }

    /// Satellite-seen bare days a year for the field's own rotation: the last 3 processed years.
    func observedBareDays(through lastYear: Int? = nil) -> (days: Int, years: [Int])? {
        guard let last = lastYear ?? self.lastYear else { return nil }
        var per: [Int: Int] = [:]
        for y in (last - 2)...last { if let v = bareDays(in: y) { per[y] = v } }
        guard !per.isEmpty else { return nil }
        let mean = Double(per.values.reduce(0, +)) / Double(per.count)
        return (Int(mean.rounded()), per.keys.sorted())
    }

    /// The green-up marker of a year, as a 10-day step.
    func greenUpDekad(_ y: Int) -> Int? {
        guard let m = year(y)?.markers.first(where: { $0.type == "green_up" && $0.date.hasPrefix(String(y)) }),
              let d = GrowerDate.parse(m.date) else { return nil }
        return GrowerDate.dekad(d)
    }

    func harvestDekad(_ y: Int) -> Int? {
        guard let m = year(y)?.markers.last(where: { $0.type == "senescence_harvest" && $0.date.hasPrefix(String(y)) }),
              let d = GrowerDate.parse(m.date) else { return nil }
        return GrowerDate.dekad(d)
    }
}

/// "early / mid / late Jun" for a 10-day step.
func dekadText(_ d: Int) -> String {
    "\(["early", "mid", "late"][d % 3]) \(GrowerDate.months[min(11, d / 3)])"
}

/// A rotation's month-by-month cover from its planting calendar (frontend api.ts monthStrip).
enum RotationStrip {
    static func months(for s: Strategy, year: Int? = nil) -> [CoverClass] {
        let y = year ?? (s.id.hasSuffix("alfalfa_break") ? 3 : 1)
        let entries = s.calendar.filter { $0.year == y }
        func md(_ text: String) -> Double {
            let p = text.split(separator: "-").compactMap { Double($0) }
            return p.count == 2 ? p[0] + (p[1] - 1) / 31 : 0
        }
        return (1...12).map { m in
            let x = Double(m) + 0.5
            let hit = entries.first { e in
                let a = md(e.plant), b = md(e.harvest)
                if a == b { return true }
                return a < b ? (x >= a && x < b) : (x >= a || x < b)
            }
            guard let hit else { return .bare }
            if hit.role == "water" { return .water }
            if hit.role == "establishing" || (abs(x - md(hit.plant)) < 1 && md(hit.plant) != md(hit.harvest)) { return .partial }
            return .covered
        }
    }
}
