import Foundation

/// "Coming season": three items (rain outlook, water supply, next season's water need).
/// Outlooks, not forecasts. Ported from frontend/app/src/components/season/ComingSeason.tsx.
struct ComingSeasonPresentation: Sendable {
    struct SeasonLean: Identifiable, Sendable, Equatable {
        let id: String
        let label: String
        /// Probability of the favoured category, percent; 33 = no lean.
        let probability: Double
        /// +1 wetter, -1 drier, 0 no lean.
        let tilt: Int
        let rainWords: String
        let tempWords: String
    }
    struct StorageBar: Identifiable, Sendable, Equatable {
        let id: String
        let name: String
        let pctOfAverage: Double
        let pctFull: Double?
        let text: String
    }
    struct NeedBar: Identifiable, Sendable, Equatable {
        let id: String
        let name: String
        let isToday: Bool
        let range: NumRange
    }
    let lede: String
    let rain: Answer
    let leans: [SeasonLean]
    let water: Answer
    let storage: [StorageBar]
    let need: Answer
    let needBars: [NeedBar]
    let limit: Double
}

enum ComingSeasonBuilder {
    static let seasonNames = ["OND": "Oct–Dec", "NDJ": "Nov–Jan", "DJF": "Dec–Feb", "JFM": "Jan–Mar", "FMA": "Feb–Apr",
                              "MAM": "Mar–May", "AMJ": "Apr–Jun", "MJJ": "May–Jul", "JJA": "Jun–Aug", "JAS": "Jul–Sep", "ASO": "Aug–Oct", "SON": "Sep–Nov"]
    private static let droughtWords = ["No_Drought": "no drought", "Persists": "the drought to stay", "Improvement": "the drought to ease",
                                       "Removal": "the drought to end", "Development": "a drought to develop"]

    static func lean(_ c: Outlook.Category?, wet: String, dry: String) -> (words: String, tilt: Int, prob: Double) {
        guard let c, !c.category.hasPrefix("equal"), c.isAbove || c.isBelow else { return ("no lean either way", 0, 33) }
        let p = c.probability?.value ?? 40
        let weak = p <= 35
        return ("\(weak ? "barely leans" : "leans") \(c.isAbove ? wet : dry) than normal", weak ? 0 : (c.isAbove ? 1 : -1), p)
    }

    static func build(outlook: Outlook, field: FieldLocation, nasaNow: NasaNow?, strategies: [Strategy]?, limit: WaterLimitStore.Limit) -> ComingSeasonPresentation {
        let seasons = Array((outlook.cpc?.seasons ?? []).prefix(4))
        let leans = seasons.map { s -> ComingSeasonPresentation.SeasonLean in
            let r = lean(s.precipitation, wet: "wetter", dry: "drier")
            let t = lean(s.temperature, wet: "warmer", dry: "cooler")
            return .init(id: s.season, label: seasonNames[s.season] ?? s.season, probability: r.prob, tilt: r.tilt, rainWords: r.words, tempWords: t.words)
        }
        let wet = leans.filter { $0.tilt > 0 }.count, dry = leans.filter { $0.tilt < 0 }.count
        let rainHead = wet > dry ? "NOAA's outlook leans wetter than normal this winter"
            : dry > wet ? "NOAA's outlook leans drier than normal this winter" : "NOAA's outlook shows no clear lean this winter"
        let rainDetail = leans.prefix(3).map { l in
            l.tilt == 0 && l.probability <= 35 ? "\(l.label): \(l.rainWords)" : "\(l.label): \(l.rainWords) (\(Int(l.probability))% chance)"
        }.joined(separator: ". ") + ". With no lean, wetter, middle and drier each have a 33% chance."
        var rainCite = "NOAA Climate Prediction Center 3-month outlooks"
        if let issued = GrowerDate.short(outlook.cpc?.issued) { rainCite += ", issued \(issued)" }
        rainCite += ". Outlooks tilt the odds; they don't say what will happen."
        let rain = Answer(id: "rain-outlook", question: "Will this winter be wetter or drier than normal?", headline: rainHead, detail: rainDetail, cite: rainCite)

        let storage = outlook.reservoirs.compactMap { r -> ComingSeasonPresentation.StorageBar? in
            guard let avg = r.pctOfAverage?.value else { return nil }
            let name = r.name.capitalized
            var text = "\(name): \(Int(avg.rounded()))% of average for the date"
            if let full = r.pctOfCapacity?.value { text += ", \(Int(full.rounded()))% full" }
            return .init(id: r.id, name: name, pctOfAverage: avg, pctFull: r.pctOfCapacity?.value, text: text)
        }
        let water = waterAnswer(outlook: outlook, field: field, nasaNow: nasaNow, storage: storage)
        let (need, bars) = needAnswer(outlook: outlook, strategies: strategies, limit: limit)
        return ComingSeasonPresentation(
            lede: "Outlooks for winter \(outlook.comingSeason.map { $0.replacingOccurrences(of: "winter ", with: "") } ?? "and next season"). They tilt the odds; they don't say what will happen.",
            rain: rain, leans: leans, water: water, storage: storage, need: need, needBars: bars, limit: limit.value
        )
    }

    static func droughtLine(_ outlook: Outlook, county: String) -> String? {
        var parts: [String] = []
        if let m = outlook.drought?.monitor, let cat = m.worstCategory {
            let words = cat.lowercased().hasPrefix("none") ? "no drought" : cat.replacingOccurrences(of: #"^D\d\s*"#, with: "", options: .regularExpression)
            parts.append("Drought Monitor: \(words) in \(m.county ?? "\(county) County")")
        }
        if let o = outlook.drought?.outlook?.seasonal, let cat = o.category {
            parts.append("NOAA expects \(droughtWords[cat] ?? cat.replacingOccurrences(of: "_", with: " ").lowercased())\(o.target.map { " through \($0)" } ?? "")")
        }
        return parts.isEmpty ? nil : parts.joined(separator: "; ") + "."
    }

    static func waterAnswer(outlook: Outlook, field: FieldLocation, nasaNow: NasaNow?, storage: [ComingSeasonPresentation.StorageBar]) -> Answer {
        let county = FieldNaming.county(field)
        let surface = field.water?.isSurface ?? true
        var head: String
        var detail: [String] = []
        var cite = "CDEC reservoir storage"
        if let d = GrowerDate.short(outlook.reservoirs.first?.latestDate) { cite += ", \(d)" }
        if surface {
            if let main = storage.first {
                head = "\(main.name) holds \(Int(main.pctOfAverage.rounded()))% of its average for the date"
                detail.append(contentsOf: storage.dropFirst().map { "\($0.name): \(Int($0.pctOfAverage.rounded()))% of average." })
            } else {
                head = "Reservoir storage hasn't loaded"
            }
            if let cvp = outlook.allocations?.cvp?.current {
                var a: [String] = []
                if let v = cvp.settlement?.value { a.append("Sacramento River settlement contractors \(Int(v))%") }
                if let v = cvp.southAg?.value { a.append("farms south of the Delta \(Int(v))%") }
                if !a.isEmpty { detail.append("Federal allocations this year: \(a.joined(separator: ", ")). Next year's are not announced yet.") }
                cite += "; Reclamation CVP allocations"
            }
        } else {
            if let g = nasaNow?.reading("grace_gw_pct")?.value {
                let words = g <= 20 ? "far below usual" : g <= 33 ? "below usual" : g < 67 ? "about usual" : "above usual"
                head = "Groundwater under this basin is \(words) (\(Units.ordinal(Int(g.rounded()))) percentile)"
                cite += "; NASA GRACE-FO groundwater, whole basin, not your own well"
            } else if let main = storage.first {
                head = "\(main.name) holds \(Int(main.pctOfAverage.rounded()))% of its average for the date"
            } else {
                head = "Water supply readings haven't loaded"
            }
            if let main = storage.first { detail.append("\(main.name): \(Int(main.pctOfAverage.rounded()))% of average for the date.") }
            if let district = field.water?.district {
                detail.append("This field pumps groundwater; \(district.replacingOccurrences(of: " (U)", with: "")) sets the pumping rules.")
            }
        }
        if let d = droughtLine(outlook, county: county) { detail.append(d); cite += "; US Drought Monitor and NOAA drought outlook" }
        return Answer(id: "water-supply", question: surface ? "Will there be water for next season?" : "How is the water supply going into winter?",
                      headline: head, detail: detail.joined(separator: " "), cite: cite + ".")
    }

    static func needAnswer(outlook: Outlook, strategies: [Strategy]?, limit: WaterLimitStore.Limit) -> (Answer, [ComingSeasonPresentation.NeedBar]) {
        let items = outlook.irrigation?.strategies ?? []
        let names = Dictionary((strategies ?? []).map { ($0.id, FieldNaming.shortRotationName($0)) }, uniquingKeysWith: { a, _ in a })
        let bars = items.compactMap { i -> ComingSeasonPresentation.NeedBar? in
            guard let r = NumRange(i.need) else { return nil }
            return .init(id: i.id, name: names[i.id] ?? i.name ?? i.id, isToday: i.isBaseline ?? false, range: r)
        }
        let cite = "Rotation model driven by NASA POWER weather, shifted by NOAA's outlook. An estimate, not a forecast."
        guard let today = bars.first(where: \.isToday) ?? bars.first else {
            return (Answer(id: "need", question: "How much water will next season need?", headline: "Next season's estimate hasn't loaded",
                           detail: "", cite: cite), bars)
        }
        let over = today.range.value - limit.value
        let year = outlook.comingSeason?.firstMatch(of: /\d{4} growing/).map { String($0.output.prefix(4)) } ?? "next season"
        let head = over > 0.05
            ? "About \(Units.oneDecimal(today.range.value)) acre-feet per acre in \(year), \(Units.oneDecimal(over)) over your limit"
            : "About \(Units.oneDecimal(today.range.value)) acre-feet per acre in \(year), within your limit"
        var detail = "That's today's rotation (\(today.name.lowercased()))"
        if today.range.hasSpread { detail += "; \(Units.oneDecimal(today.range.low))–\(Units.oneDecimal(today.range.high)) across the outlook scenarios" }
        detail += ". Your limit is \(Units.oneDecimal(limit.value))\(limit.isExample ? " (an example, change it on Compare)" : "")."
        if let best = bars.filter({ !$0.isToday }).min(by: { $0.range.value < $1.range.value }), best.range.value < today.range.value - 0.3 {
            detail += " \(best.name) would need about \(Units.oneDecimal(best.range.value))."
        }
        return (Answer(id: "need", question: "How much water will next season need?", headline: head, detail: detail, cite: cite,
                       tone: over > 0.05 ? .warn : .normal), bars)
    }
}
