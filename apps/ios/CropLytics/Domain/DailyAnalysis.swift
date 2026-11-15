import Foundation

/// Grower-unit summaries from the daily record (frontend/app/src/season.ts). Every result says which season it
/// describes and how "normal" was built. Pure functions over ISO date strings (YYYY-MM-DD sort as dates).
enum DailyAnalysis {
    /// 104 °F (40 °C), NOAA / ECCC station highs (PLAN.md, 14 Nov).
    static let hotC = 40.0, hotF = 104

    struct Period: Equatable, Sendable {
        let label: String
        let from: String
        let to: String
        let current: Bool
    }

    private static func iso(_ d: Date) -> String {
        let c = GrowerDate.calendar.dateComponents([.year, .month, .day], from: d)
        return String(format: "%04d-%02d-%02d", c.year ?? 2026, c.month ?? 1, c.day ?? 1)
    }

    private static func shift(_ iso: String, years k: Int) -> String {
        guard let y = Int(iso.prefix(4)) else { return iso }
        return String(y - k) + iso.dropFirst(4)
    }

    /// Rain season (1 Oct to 30 Sep) or calendar year, up to the cut-off; the last complete one if the record stops first.
    static func period(rows: [DailyRecord.Row], cutoff: Date, water: Bool) -> Period? {
        guard let first = rows.first?.date, let last = rows.last?.date else { return nil }
        let cut = iso(cutoff)
        let cy = Int(cut.prefix(4)) ?? 2026, cm = Int(cut.dropFirst(5).prefix(2)) ?? 1
        let startY = water ? (cm >= 10 ? cy : cy - 1) : cy
        let from = water ? "\(startY)-10-01" : "\(startY)-01-01"
        let startLabel = water ? "1 Oct \(startY)" : "1 Jan \(startY)"
        if last >= cut && first <= from { return Period(label: "since \(startLabel)", from: from, to: cut, current: true) }
        if last >= from && first <= from {
            return Period(label: "\(startLabel) to \(GrowerDate.shortNoYear(last) ?? last)", from: from, to: last, current: true)
        }
        let lastY = Int(last.prefix(4)) ?? cy
        if water {
            let e = last.dropFirst(5) >= "09-30" ? lastY : lastY - 1
            return Period(label: "last season, Oct \(e - 1) to Sep \(e)", from: "\(e - 1)-10-01", to: "\(e)-09-30", current: false)
        }
        let e = last.dropFirst(5) >= "12-31" ? lastY : lastY - 1
        return Period(label: "last year, \(e)", from: "\(e)-01-01", to: "\(e)-12-31", current: false)
    }

    private static func sum(_ rows: [DailyRecord.Row], _ from: String, _ to: String, _ f: (DailyRecord.Row) -> Double?) -> (s: Double, n: Int) {
        var s = 0.0, n = 0
        for r in rows where r.date >= from && r.date <= to { if let v = f(r) { s += v; n += 1 } }
        return (s, n)
    }

    /// The same window in each earlier season with full data.
    private static func normal(_ rows: [DailyRecord.Row], _ p: Period, count: Bool = false, _ f: (DailyRecord.Row) -> Double?) -> (mean: Double?, seasons: Int) {
        guard let first = rows.first?.date, let last = rows.last?.date else { return (nil, 0) }
        var vals: [Double] = []
        for k in 1...30 {
            let from = shift(p.from, years: k), to = shift(p.to, years: k)
            if from < first || to > last { continue }
            let r = sum(rows, from, to, f)
            vals.append(count ? Double(r.n) : r.s)
        }
        return (vals.isEmpty ? nil : vals.reduce(0, +) / Double(vals.count), vals.count)
    }

    struct RainSoFar: Sendable, Equatable {
        let period: Period
        let inches: Double
        let normal: Double?
        let seasons: Int
        var pct: Double? { normal.flatMap { $0 > 0 ? inches / $0 * 100 : nil } }
    }

    /// Rain so far this rain season at a date: NASA IMERG over the field (else the station mean); normal = the same dates before.
    static func rainSoFar(_ daily: DailyRecord, at t: TimePoint) -> RainSoFar? {
        let rows = daily.rows.filter { $0.rainMm != nil }
        guard let p = period(rows: rows, cutoff: t.endDate, water: true) else { return nil }
        let s = sum(rows, p.from, p.to) { $0.rainMm }.s
        let n = normal(rows, p) { $0.rainMm }
        return RainSoFar(period: p, inches: Units.inches(fromMM: s), normal: n.mean.map(Units.inches(fromMM:)), seasons: n.seasons)
    }

    struct HeatFrost: Sendable, Equatable {
        let period: Period
        let hot: Int
        let hotNormal: Double?
        let frostPeriod: Period
        let frost: Int
        let frostNormal: Double?
    }

    /// Hot days (station high >= 104 °F) this calendar year and frost nights (<= 32 °F) this rain season, against normal.
    static func heatFrost(_ daily: DailyRecord, at t: TimePoint) -> HeatFrost? {
        let rows = daily.rows.filter { $0.tmaxC != nil }
        guard let p = period(rows: rows, cutoff: t.endDate, water: false), let pf = period(rows: rows, cutoff: t.endDate, water: true) else { return nil }
        let hotF: (DailyRecord.Row) -> Double? = { ($0.tmaxC ?? -99) >= hotC ? 1 : nil }
        let frostF: (DailyRecord.Row) -> Double? = { r in r.tminC.map { $0 * 9 / 5 + 32 <= 32 ? 1 : nil } ?? nil }
        func zeroFilled(_ per: Period, _ f: (DailyRecord.Row) -> Double?) -> Double? {
            guard let first = rows.first?.date, let last = rows.last?.date else { return nil }
            var total = 0, seasons = 0
            for k in 1...30 {
                let from = shift(per.from, years: k), to = shift(per.to, years: k)
                if from < first || to > last { continue }
                seasons += 1; total += sum(rows, from, to, f).n
            }
            return seasons == 0 ? nil : Double(total) / Double(seasons)
        }
        return HeatFrost(period: p, hot: sum(rows, p.from, p.to, hotF).n, hotNormal: zeroFilled(p, hotF),
                         frostPeriod: pf, frost: sum(rows, pf.from, pf.to, frostF).n, frostNormal: zeroFilled(pf, frostF))
    }

    /// The latest soil-moisture and groundwater percentiles at or before a date (at most 6 months back).
    static func readings(_ daily: DailyRecord, at t: TimePoint) -> (soil: (Double, String)?, groundwater: (Double, String)?) {
        let cut = iso(t.endDate)
        let floor = iso(t.endDate.addingTimeInterval(-183 * 86_400))
        var soil: (Double, String)?, gw: (Double, String)?
        for r in daily.rows.reversed() where r.date <= cut {
            if r.date < floor { break }
            if soil == nil, let v = r.smapPct { soil = (v, r.date) }
            if gw == nil, let v = r.gracePct { gw = (v, r.date) }
            if soil != nil && gw != nil { break }
        }
        return (soil, gw)
    }

    /// Days with 1 inch (25.4 mm) of rain or more in a year, as (10-day step, date).
    static func heavyRainDays(_ daily: DailyRecord, year: Int) -> [(dekad: Int, date: String)] {
        let prefix = String(year)
        return daily.rows.filter { $0.date.hasPrefix(prefix) && ($0.rainMm ?? 0) >= 25.4 }.compactMap { r in
            GrowerDate.parse(r.date).map { (GrowerDate.dekad($0), r.date) }
        }
    }
}
