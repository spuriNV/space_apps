import Foundation

/// "Compare": today's rotation against the top alternatives, as what you gain and what you give up,
/// in acre-feet and days. A gain counts only when the likely ranges don't overlap.
/// Ported from frontend/app/src/components/compare/ComparePanel.tsx.
enum Verdict: Sendable, Equatable { case better, worse, unclear, same, none }

struct TradeLine: Identifiable, Sendable, Equatable {
    let id: String
    let title: String
    let delta: String
}

struct RotationSummary: Identifiable, Sendable {
    let id: String
    let name: String
    let fullName: String
    let isToday: Bool
    let months: [CoverClass]
    let water: NumRange?
    let bareDays: NumRange?
    let bareDaysSeen: Bool
    let rainOnBareDays: NumRange?
    let fit: Fit
    let rank: Int?
    let scores: [ScoreLine]
    var rainFed = false
    /// "1.9 acre-ft/acre" or "Rain-fed (no irrigation)".
    var waterText: String {
        if rainFed { return FieldNowBuilder.rainFedText }
        return water.map { "\(Units.oneDecimal($0.value)) acre-ft/acre" } ?? "not scored yet"
    }

    enum Fit: Sendable, Equatable {
        case fits, mayExceed, over, unknown
        var text: String {
            switch self {
            case .fits: "Fits your limit"
            case .mayExceed: "May go over your limit"
            case .over: "Over your limit"
            case .unknown: "Water need not scored"
            }
        }
    }

    struct ScoreLine: Identifiable, Sendable {
        let id: String
        let label: String
        let value: NumRange
    }
}

struct AlternativeComparison: Identifiable, Sendable {
    let option: RotationSummary
    let gains: [TradeLine]
    let losses: [TradeLine]
    let unclear: [String]
    var id: String { option.id }
    /// One-sentence lead for the card and the summary page.
    var lead: String {
        let g = gains.first.map { "\($0.title.lowercased()), \($0.delta)" } ?? "nothing clearly better"
        let l = losses.first.map { "\($0.title.lowercased()), \($0.delta)" } ?? "nothing clearly worse"
        return "You'd gain: \(g). You'd give up: \(l)."
    }
}

struct ComparePresentation: Sendable {
    let today: RotationSummary
    let top: [AlternativeComparison]
    let all: [RotationSummary]
    let openETLine: String
}

enum CompareBuilder {
    /// Weather to score in: a typical year, or the engine's replay of 2022 (dry) or 2023 (wet).
    enum Weather: String, CaseIterable, Sendable, Hashable {
        case typical, dry = "2022", wet = "2023"
        var title: String { self == .typical ? "Typical year" : self == .dry ? "Dry, like 2022" : "Wet, like 2023" }
        var short: String { self == .typical ? "Typical" : self == .dry ? "Dry 2022" : "Wet 2023" }
    }

    struct Context: Sendable {
        /// Satellite-seen bare days for today's rotation (the others are modelled).
        var todayBare: (days: Int, years: [Int])?
        var weather: Weather = .typical
    }

    static func waterNeed(_ s: Strategy, _ w: Weather) -> NumRange? {
        let n = w == .typical ? s.water.irrigationNeedMm : (s.exposure.replay[w.rawValue]?.irrigationNeedMm ?? s.water.irrigationNeedMm)
        return NumRange(n)?.map(Units.acreFeetPerAcre(fromMM:))
    }

    private struct Metric: Sendable {
        let key: String
        let label: String
        let isAcreFeet: Bool
        let gain: String
        let loss: String
        let get: @Sendable (Strategy, Context) -> NumRange?
    }

    private static let metrics: [Metric] = [
        Metric(key: "water", label: "Irrigation water needed", isAcreFeet: true, gain: "Needs less irrigation water", loss: "Needs more irrigation water") { s, ctx in
            s.isRainFed ? NumRange(0) : waterNeed(s, ctx.weather)
        },
        Metric(key: "bare", label: "Days the field sits bare", isAcreFeet: false, gain: "Field bare fewer days", loss: "Field bare more days") { s, ctx in
            if s.isBaseline, let seen = ctx.todayBare { return NumRange(Double(seen.days)) }
            return NumRange(s.exposure.bareDaysPerYear)
        },
        Metric(key: "rain", label: "Heavy rain on bare soil", isAcreFeet: false, gain: "Less heavy rain on bare soil", loss: "More heavy rain on bare soil") { s, ctx in
            NumRange(ctx.weather == .typical ? s.exposure.exposedRainDays : (s.exposure.replay[ctx.weather.rawValue]?.exposedRainDays ?? s.exposure.exposedRainDays))
        },
    ]

    static let scoreLabels: [(String, String)] = [
        ("forage_value", "Feed you can cut or graze"), ("n_fixation", "Adds nitrogen"), ("erosion", "Protects soil from washing away"),
        ("organic_matter", "Builds organic matter"), ("market", "Crops you can sell locally"), ("pest_break", "Breaks pest cycles"),
        ("infiltration", "Water soaks in"), ("n_scavenging", "Holds nitrogen over winter"),
    ]

    /// Better / worse only when the whole likely ranges sit apart (lower is better for water and days).
    static func verdict(_ a: NumRange?, _ b: NumRange?, higherIsBetter: Bool = false) -> Verdict {
        guard let a, let b else { return .none }
        if a.low == b.low && a.high == b.high && a.value == b.value { return .same }
        if a.low > b.high { return higherIsBetter ? .better : .worse }
        if a.high < b.low { return higherIsBetter ? .worse : .better }
        if a.low == a.high && b.low == b.high { return (a.value > b.value) == higherIsBetter ? .better : .worse }
        return .unclear
    }

    static func deltaText(_ a: Double, _ b: Double, acreFeet: Bool) -> String {
        let d = abs(a - b)
        if acreFeet { return "about \(Units.oneDecimal(d)) acre-ft/acre \(a < b ? "less" : "more") a year (\(Int((d * 12).rounded())) in)" }
        let n = d < 10 ? String(format: "%.1f", d) : String(Int(d.rounded()))
        return "about \(n) \(a < b ? "fewer" : "more") days a year"
    }

    static func fit(_ water: NumRange?, limit: Double) -> RotationSummary.Fit {
        guard let w = water else { return .unknown }
        if w.high <= limit { return .fits }
        if w.low > limit { return .over }
        return .mayExceed
    }

    static func summary(_ s: Strategy, ctx: Context, limit: Double) -> RotationSummary {
        let water = metrics[0].get(s, ctx)
        let scores = scoreLabels.compactMap { key, label -> RotationSummary.ScoreLine? in
            guard let r = NumRange(s.scores[key]) else { return nil }
            return .init(id: key, label: label, value: r)
        }
        return RotationSummary(
            id: s.id, name: FieldNaming.shortRotationName(s), fullName: s.name, isToday: s.isBaseline,
            months: RotationStrip.months(for: s), water: water, bareDays: metrics[1].get(s, ctx),
            bareDaysSeen: s.isBaseline && ctx.todayBare != nil, rainOnBareDays: metrics[2].get(s, ctx),
            fit: s.isRainFed ? .fits : fit(water, limit: limit), rank: s.composite?.rank, scores: scores, rainFed: s.isRainFed
        )
    }

    static func compare(_ alt: Strategy, to today: Strategy, ctx: Context, limit: Double) -> AlternativeComparison {
        var gains: [TradeLine] = [], losses: [TradeLine] = [], unclear: [String] = []
        for m in metrics {
            let a = m.get(alt, ctx), b = m.get(today, ctx)
            switch verdict(a, b) {
            case .better: gains.append(TradeLine(id: m.key, title: m.gain, delta: deltaText(a!.value, b!.value, acreFeet: m.isAcreFeet)))
            case .worse: losses.append(TradeLine(id: m.key, title: m.loss, delta: deltaText(a!.value, b!.value, acreFeet: m.isAcreFeet)))
            case .unclear, .same: unclear.append(m.label)
            case .none: break
            }
        }
        return AlternativeComparison(option: summary(alt, ctx: ctx, limit: limit), gains: gains, losses: losses, unclear: unclear)
    }

    static func build(strategies: [Strategy], calendar: FieldCalendar?, limit: Double, count: Int = 2, weather: Weather = .typical) -> ComparePresentation? {
        guard let today = strategies.first(where: \.isBaseline) ?? strategies.first else { return nil }
        let ctx = Context(todayBare: calendar?.observedBareDays(), weather: weather)
        // Best overall score first; on a tie, the one that needs less water.
        func key(_ s: Strategy) -> (Double, Double) {
            let score: Double = s.composite?.value ?? 0
            let water: Double = s.water.irrigationNeedMm.value ?? 0
            return (score, -water)
        }
        let alternatives = strategies.filter { $0.id != today.id }.sorted { key($0) > key($1) }
        let top = alternatives.prefix(count).map { compare($0, to: today, ctx: ctx, limit: limit) }
        let all = ([today] + alternatives).map { summary($0, ctx: ctx, limit: limit) }
        return ComparePresentation(today: summary(today, ctx: ctx, limit: limit), top: top, all: all, openETLine: openETLine(today))
    }

    /// Honest line on how the water model compares with OpenET measured water use on this field.
    static func openETLine(_ today: Strategy) -> String {
        guard let v = today.water.etcVsOpenetPct?.value else { return "Not yet checked against measured water use (OpenET) on this field." }
        let r = Int(abs(v).rounded())
        return "Checked against OpenET satellite measurements of this field: our estimate runs about \(r)% \(v >= 0 ? "high, as expected for a fully watered crop" : "low")."
    }
}
