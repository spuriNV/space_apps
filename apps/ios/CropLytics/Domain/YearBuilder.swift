import Foundation

/// "This field's year": a typical-year strip, one strip per season (the last 4 by default), one sentence on what's
/// different, heavy-rain days marked, and the machine-learning calendar as a comparison (frontend YearSheet.tsx).
struct YearPresentation: Sendable {
    struct Row: Identifiable, Sendable {
        let year: Int
        let crop: String
        let strip: [CoverClass]
        let ml: [CoverClass]?
        let ticks: [StripTick]
        let bareDays: Int?
        let rainOnBare: String
        var id: Int { year }
    }
    let lede: String
    let typical: [CoverClass]
    let typicalLabel: String
    let typicalBareDays: Int?
    let rows: [Row]
    let mlVerdict: MLVerdict
}

struct MLVerdict: Sendable, Equatable {
    let available: Bool
    let short: String
    let long: String
    let warn: Bool
}

enum YearBuilder {
    static let mlTarget = (accuracy: 0.85, f1: 0.8)

    static func typical(_ years: [[CoverClass]]) -> [CoverClass] {
        (0..<36).map { d in
            var n: [CoverClass: Int] = [:]
            for y in years where d < y.count && y[d] != .noView { n[y[d], default: 0] += 1 }
            return n.max { a, b in a.value == b.value ? a.key.rawValue > b.key.rawValue : a.value < b.value }?.key ?? .noView
        }
    }

    static func bareDays(_ steps: [CoverClass]) -> Int? {
        let clear = steps.filter { $0 != .noView }.count
        guard clear >= 18 else { return nil }
        return Int((Double(steps.filter { $0 == .bare }.count) / Double(clear) * 365).rounded())
    }

    static func mlVerdict(models: ModelReport?, ml: MLCalendar?, gap: FieldLocation.DataGap?) -> MLVerdict {
        guard let ml else {
            if let gap { return MLVerdict(available: false, short: "Not available in BC", long: "Not available in BC. \(gap.reason ?? "")", warn: false) }
            return MLVerdict(available: false, short: "Not ready for this field yet", long: "The machine-learning calendar is not ready for this field yet.", warn: false)
        }
        let agree = ml.disagreePct.map { " The two disagree on \(Int($0.rounded()))% of clear satellite days." } ?? ""
        if ml.source == "estimate" {
            return MLVerdict(available: true, short: "An estimate, not a trained model", long: "A simpler two-class greenness rule run on this field only.\(agree)", warn: false)
        }
        let method = ml.detector ?? "random_forest"
        let m = models?.items.first { $0.task == "bare_cover" && $0.method == method && $0.id.contains("_year_") }
        let acc = m?.metrics["accuracy_2022"], f1 = m?.metrics["f1_bare_2022"]
        let pct = { (x: Double?) in x.map { "\(Int(($0 * 100).rounded()))%" } ?? "?" }
        if let acc, let f1, acc >= mlTarget.accuracy, f1 >= mlTarget.f1 {
            if acc > 0.97 {
                return MLVerdict(available: true, short: "Second opinion only", long: "In 2022, a year it never trained on, it scored \(pct(acc)). That is too good to take at face value: the model partly learned how its training labels were made. Shown as a second opinion next to the rule, not as the answer.\(agree)", warn: false)
            }
            return MLVerdict(available: true, short: "Meets accuracy target", long: "Meets our accuracy target on this field (right \(pct(acc)) of the time in 2022, a year it never trained on). Shown next to the rule as a comparison.\(agree)", warn: false)
        }
        return MLVerdict(available: true, short: "Below accuracy target", long: "Below our accuracy target on this field: in 2022, a year it never trained on, it was right \(pct(acc)) of the time against a target of 85%. The rule calendar stays the answer; this is for comparison only.\(agree)", warn: true)
    }

    static func build(field: FieldLocation, calendar: FieldCalendar, ml: MLCalendar?, models: ModelReport?, daily: DailyRecord?,
                      stress: StressReport?, waterSeen: WaterSeen?, today: TimePoint, earlier: Bool, detail: Bool) -> YearPresentation {
        let last = calendar.lastYear ?? today.year
        let allYears = calendar.years.map(\.year).sorted()
        let past = allYears.filter { $0 <= last }.map { calendar.classes(for: $0) }.filter { $0.filter { $0 != .noView }.count > 6 }
        let typ = typical(past)
        let pastYears = allYears.filter { $0 <= last }
        let lastStrip = calendar.classes(for: last)
        func days(_ s: [CoverClass], _ c: CoverClass) -> Int { s.filter { $0 == c }.count * 10 }
        let dBare = days(lastStrip, .bare) - days(typ, .bare), dWater = days(lastStrip, .water) - days(typ, .water)
        var lede = abs(dBare) >= 20 ? "\(last) had about \(abs(dBare)) \(dBare > 0 ? "more" : "fewer") bare days than a typical year"
            : abs(dWater) >= 20 ? "\(last) was flooded about \(abs(dWater)) days \(dWater > 0 ? "longer" : "less") than a typical year"
            : "\(last) looked much like a typical year"
        lede += "."
        if let up = calendar.greenUpDekad(last) { lede += " Green from \(dekadText(up))." }
        if last < today.year { lede += " \(last + 1) not processed yet." }

        let from = earlier ? TimePoint.firstYear : today.year - 3
        let shown = Array(Set(allYears + [today.year])).filter { $0 >= from && $0 <= today.year }.sorted(by: >)
        let rows = shown.map { y -> YearPresentation.Row in
            let strip = calendar.classes(for: y)
            var ticks: [StripTick] = []
            var rainLine = "–"
            if let daily {
                let rd = DailyAnalysis.heavyRainDays(daily, year: y)
                let hits = rd.filter { $0.dekad < strip.count && strip[$0.dekad] == .bare }.count
                ticks += rd.map { StripTick(index: $0.dekad, kind: .rain(hitBare: $0.dekad < strip.count && strip[$0.dekad] == .bare)) }
                if strip.contains(where: { $0 != .noView }) { rainLine = "\(hits) of \(rd.count)" }
            }
            if detail {
                for s in waterSeen?.scenes ?? [] where s.date.hasPrefix(String(y)) && (s.waterFrac ?? 0) >= 0.5 {
                    if let d = GrowerDate.parse(s.date) { ticks.append(StripTick(index: GrowerDate.dekad(d), kind: .water)) }
                }
                for w in stress?.weeks ?? [] where (w.flagZscore || w.flagIforest) && (w.weekStart ?? "").hasPrefix(String(y)) {
                    if let d = GrowerDate.parse(w.weekStart) { ticks.append(StripTick(index: GrowerDate.dekad(d), kind: .stress)) }
                }
            }
            let mlStrip = ml.map { $0.calendar.classes(for: y) }
            let crop = field.cropHistory[String(y)].map(FieldNaming.cropName) ?? "Crop map not out yet"
            return .init(year: y, crop: crop, strip: strip, ml: mlStrip, ticks: ticks,
                         bareDays: strip.contains { $0 != .noView } ? bareDays(strip) : nil, rainOnBare: rainLine)
        }
        let label = pastYears.first.map { "most common, \($0)–\(String(last).suffix(2))" } ?? "most common"
        return YearPresentation(lede: lede, typical: typ, typicalLabel: label, typicalBareDays: bareDays(typ), rows: rows,
                                mlVerdict: mlVerdict(models: models, ml: ml, gap: field.gap("ml_calendar")))
    }
}
