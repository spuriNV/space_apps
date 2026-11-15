import Foundation

/// "Your field now" (or "Your field in mid Jul 2023"): a compact visual summary, then plain answers.
/// Farmer default: what's growing, rain, water limit, soil and groundwater, the soil itself.
/// Adviser detail (More detail on): green cover, hot days and frost, crop stress and standing water.
/// Pure function of the API data, ported from frontend/app/src/components/ui/FieldNow.tsx.
struct FieldNowPresentation: Sendable {
    struct Summary: Sendable {
        let stripYear: Int
        let strip: [CoverClass]
        let marker: Int
        let stage: String
        let stageClass: CoverClass
        let rain: Meter?
        let water: Meter?
        let greenness: Meter?
        let soilPercentile: Double?
        let groundwaterPercentile: Double?
    }
    let heading: String
    let summary: Summary
    let answers: [Answer]
}

enum FieldNowBuilder {
    struct Input {
        var field: FieldLocation
        var nasaNow: NasaNow?
        var calendar: FieldCalendar?
        var strategies: [Strategy]?
        var limit: WaterLimitStore.Limit
        var t: TimePoint
        var today: TimePoint
        var daily: DailyRecord? = nil
        var stress: StressReport? = nil
        var waterSeen: WaterSeen? = nil

        init(field: FieldLocation, nasaNow: NasaNow?, calendar: FieldCalendar?, strategies: [Strategy]?, limit: WaterLimitStore.Limit,
             t: TimePoint, today: TimePoint, daily: DailyRecord? = nil, stress: StressReport? = nil, waterSeen: WaterSeen? = nil) {
            self.field = field; self.nasaNow = nasaNow; self.calendar = calendar; self.strategies = strategies; self.limit = limit
            self.t = t; self.today = today; self.daily = daily; self.stress = stress; self.waterSeen = waterSeen
        }

        /// Convenience for "today" callers.
        init(field: FieldLocation, nasaNow: NasaNow?, calendar: FieldCalendar?, strategies: [Strategy]?, limit: WaterLimitStore.Limit, today: Date) {
            let t = TimePoint(date: today)
            self.init(field: field, nasaNow: nasaNow, calendar: calendar, strategies: strategies, limit: limit, t: t, today: t)
        }

        var isToday: Bool { t == today }
    }

    static func build(_ input: Input) -> FieldNowPresentation {
        let stage = stage(input)
        let soilGw = soilAndGroundwater(input)
        let summary = FieldNowPresentation.Summary(
            stripYear: input.t.year, strip: input.calendar?.classes(for: input.t.year) ?? Array(repeating: .noView, count: 36),
            marker: input.t.dekad, stage: stage.text, stageClass: stage.cls,
            rain: rainMeter(rain(input)), water: waterMeter(input.strategies, limit: input.limit), greenness: greennessMeter(input),
            soilPercentile: soilGw.soil?.value, groundwaterPercentile: soilGw.groundwater?.value
        )
        var answers: [Answer] = [growingAnswer(input, stage: stage)]
        if let g = greenAnswer(input) { answers.append(g) }
        answers.append(rainAnswer(input))
        if let a = waterAnswer(input.strategies, limit: input.limit) { answers.append(a) }
        answers.append(soilAnswer(input, soilGw))
        if let s = soilKindAnswer(input.field) { answers.append(s) }
        if let st = stressAnswer(input) { answers.append(st) }
        if let h = heatAnswer(input) { answers.append(h) }
        return FieldNowPresentation(heading: input.isToday ? "Your field now" : "Your field in \(input.t.label)", summary: summary, answers: answers)
    }

    static func cropMapName(_ f: FieldLocation) -> String { f.isBC ? "AAFC Annual Crop Inventory" : "USDA Cropland Data Layer" }
    static func stationsName(_ f: FieldLocation) -> String { f.isBC ? "Environment Canada weather stations near the field" : "NOAA weather stations near the field" }

    // MARK: Stage

    struct Stage { let text: String; let sub: String; let cls: CoverClass; let date: Date?; let ndvi: Double? }

    static func stage(_ input: Input) -> Stage {
        let cutoff = input.t.endDate
        if let cal = input.calendar, let obs = cal.latestObservation(before: cutoff), cutoff.timeIntervalSince(obs.date) < 45 * 86_400 {
            let y = GrowerDate.year(obs.date), d = GrowerDate.dekad(obs.date)
            let smoothed = cal.classes(for: y)[d]
            return describe(smoothed == .noView ? obs.cls : smoothed, dekad: d, greenUp: cal.greenUpDekad(y), harvest: cal.harvestDekad(y), date: obs.date, ndvi: obs.ndvi)
        }
        if let cal = input.calendar {
            // No observation within 6 weeks: the smoothed calendar class at the date, if the satellites saw anything.
            let c = cal.classes(for: input.t.year)[input.t.dekad]
            if c != .noView { return describe(c, dekad: input.t.dekad, greenUp: cal.greenUpDekad(input.t.year), harvest: cal.harvestDekad(input.t.year), date: nil, ndvi: nil) }
        }
        if input.isToday, let r = input.nasaNow?.reading("hls_ndvi"), let v = r.value {
            let cls: CoverClass = v < 0.2 ? .bare : v < 0.35 ? .partial : .covered
            let date = GrowerDate.parse(r.obsDate)
            return describe(cls, dekad: date.map(GrowerDate.dekad) ?? input.t.dekad, greenUp: nil, harvest: nil, date: date, ndvi: v)
        }
        return Stage(text: "No clear satellite view", sub: "Clouds, or no image within 6 weeks of the date.", cls: .noView, date: nil, ndvi: nil)
    }

    static func describe(_ cls: CoverClass, dekad d: Int, greenUp: Int?, harvest: Int?, date: Date?, ndvi: Double?) -> Stage {
        switch cls {
        case .water:
            return Stage(text: "Under water", sub: d >= 30 || d <= 5 ? "Flooded for the winter, as in most years." : "Standing water on the field.", cls: cls, date: date, ndvi: ndvi)
        case .covered:
            if let up = greenUp, d >= up, harvest.map({ d < $0 }) ?? true {
                return Stage(text: "Crop growing, green since \(dekadText(up))", sub: "", cls: cls, date: date, ndvi: ndvi)
            }
            return Stage(text: "Full green cover", sub: "", cls: cls, date: date, ndvi: ndvi)
        case .partial:
            return Stage(text: "Thin cover", sub: "Some green, less than a full crop: a young crop, regrowth after a cutting, stubble or weeds.", cls: cls, date: date, ndvi: ndvi)
        case .bare:
            if let h = harvest, d > h { return Stage(text: "Bare since harvest in \(dekadText(h))", sub: "", cls: cls, date: date, ndvi: ndvi) }
            return Stage(text: "Bare ground", sub: "", cls: cls, date: date, ndvi: ndvi)
        case .noView:
            return Stage(text: "No clear satellite view", sub: "Clouds, or no image within 6 weeks of the date.", cls: cls, date: date, ndvi: ndvi)
        }
    }

    static func satelliteName(_ cal: FieldCalendar?) -> String {
        cal?.source == "hls" ? "NASA/USGS HLS satellites (Landsat and Sentinel-2)" : "Landsat (NASA/USGS) and Sentinel-2 satellites"
    }

    static func growingAnswer(_ input: Input, stage: Stage) -> Answer {
        let year = input.t.year
        var detail: String
        if let crop = input.field.cropHistory[String(year)] {
            detail = "\(FieldNaming.cropName(crop)) on record for \(year)."
        } else if let latest = FieldNaming.latestCrop(input.field.cropHistory) {
            detail = "The \(year) crop map isn't out yet (\(input.field.isBC ? "AAFC" : "USDA"), early \(year + 1)). \(latest.year): \(latest.crop.lowercased())."
        } else {
            detail = "No crop on record."
        }
        if !stage.sub.isEmpty { detail += " " + stage.sub }
        var cite = "\(satelliteName(input.calendar)), 100 ft squares; crop from the \(cropMapName(input.field))."
        if let d = stage.date {
            let days = Int(input.t.endDate.timeIntervalSince(d) / 86_400)
            cite += " Latest clear view \(GrowerDate.short(d))\(days < 8 ? "" : days < 14 ? ", about a week before" : ", about \(days / 7) weeks before")."
        }
        return Answer(id: "growing", question: "What is growing, and how far along?", headline: stage.text, detail: detail, cite: cite)
    }

    static func greenAnswer(_ input: Input) -> Answer? {
        let st = stage(input)
        guard let v = st.ndvi, st.cls != .water, st.cls != .noView else { return nil }
        let head = v >= 0.6 ? "Full green canopy" : v >= 0.35 ? "Partly green" : v >= 0.2 ? "Thin green cover" : "Little or no green cover"
        return Answer(id: "green", question: "How much green cover is there?", headline: head,
                      detail: "Greenness \(String(format: "%.2f", v)) on a 0 to 1 scale; above 0.6 is a full canopy.",
                      cite: "Greenness from \(satelliteName(input.calendar)), field average\(st.date.map { ", \(GrowerDate.short($0))" } ?? "").",
                      detailOnly: true)
    }

    // MARK: Rain

    struct Rain { let inches: Double; let normal: Double?; let label: String; let current: Bool; let fromSatellite: Bool; let seasons: Int
        var pct: Double? { normal.flatMap { $0 > 0 ? inches / $0 * 100 : nil } }
    }

    static func rain(_ input: Input) -> Rain? {
        if input.isToday, let r = input.nasaNow?.reading("imerg_wy_to_date_mm"), let mm = r.value,
           let n = input.nasaNow?.reading("imerg_wy_to_date_normal_mm")?.value, n > 0 {
            return Rain(inches: Units.inches(fromMM: mm), normal: Units.inches(fromMM: n), label: "since 1 Oct", current: true, fromSatellite: true, seasons: 25)
        }
        if let daily = input.daily, let r = DailyAnalysis.rainSoFar(daily, at: input.t) {
            let sat = daily.rows.contains { $0.imergMm != nil }
            return Rain(inches: r.inches, normal: r.normal, label: r.period.current ? "since 1 Oct" : r.period.label, current: r.period.current, fromSatellite: sat, seasons: r.seasons)
        }
        return nil
    }

    static func rainMeter(_ r: Rain?) -> Meter? {
        guard let r else { return nil }
        let normal = r.normal ?? r.inches
        return Meter(label: "Rain \(r.current ? "since 1 Oct" : r.label)", valueText: "\(Units.inchesText(r.inches)) in", value: r.inches,
                     reference: r.normal, referenceLabel: "normal", scaleMax: max(r.inches, normal) * 1.25,
                     note: r.pct.map { "\(Int($0.rounded()))% of normal" } ?? "Normal not known")
    }

    static func rainAnswer(_ input: Input) -> Answer {
        guard let r = rain(input) else {
            return Answer(id: "rain", question: "How much rain so far this season?", headline: "No rain reading yet",
                          detail: "The rain record for this season hasn't loaded.", cite: "NASA GPM IMERG satellite rain.")
        }
        let words = r.pct.map { $0 >= 115 ? "wetter than normal" : $0 <= 85 ? "drier than normal" : "about normal" }
        let head = words.map { r.current ? "So far \($0)" : "Last season was \($0)" } ?? "\(Units.inchesText(r.inches)) inches"
        var detail = "\(Units.inchesText(r.inches)) in \(r.label)."
        if let n = r.normal { detail += " Normal: \(Units.inchesText(n)) in." }
        let cite = r.fromSatellite
            ? "NASA GPM IMERG satellite rain over the field (one reading for a 6-mile square); normal = the same dates in the \(r.seasons) seasons before."
            : "\(stationsName(input.field)), averaged; normal = the same dates in earlier seasons."
        return Answer(id: "rain", question: "How much rain so far this season?", headline: head, detail: detail, cite: cite)
    }

    // MARK: Water need vs limit

    static func baseline(_ strategies: [Strategy]?) -> Strategy? { strategies?.first(where: \.isBaseline) ?? strategies?.first }

    static let rainFedText = "Rain-fed (no irrigation)"

    static func waterMeter(_ strategies: [Strategy]?, limit: WaterLimitStore.Limit) -> Meter? {
        guard let base = baseline(strategies), let need = base.water.irrigationNeedMm.value else { return nil }
        if base.isRainFed {
            return Meter(label: "Water need, a year", valueText: rainFedText, value: 0, reference: limit.value, referenceLabel: "your limit",
                         scaleMax: max(limit.value, 1) * 1.2, note: "Limit \(Units.oneDecimal(limit.value))\(limit.isExample ? " (example)" : "")")
        }
        let af = Units.acreFeetPerAcre(fromMM: need)
        return Meter(label: "Water need, a year", valueText: "\(Units.oneDecimal(af)) acre-ft/acre", value: af,
                     reference: limit.value, referenceLabel: "your limit", scaleMax: max(af, limit.value) * 1.2,
                     note: "Limit \(Units.oneDecimal(limit.value))\(limit.isExample ? " (example)" : "")", warn: af > limit.value)
    }

    static func waterAnswer(_ strategies: [Strategy]?, limit: WaterLimitStore.Limit) -> Answer? {
        guard let base = baseline(strategies), let range = NumRange(base.water.irrigationNeedMm) else { return nil }
        let example: AnswerStatus? = limit.isExample ? AnswerStatus(kind: .example, text: "example, change it on Compare") : nil
        let cite = "Rotation model with NASA POWER weather: crop water use minus rain, typical year 2015–2025."
        if base.isRainFed {
            return Answer(id: "water", question: "Will the water limit cover irrigation?", headline: "Fits any limit",
                          detail: "\(rainFedText). Limit: \(Units.oneDecimal(limit.value)).", cite: cite, status: example)
        }
        let af = range.map(Units.acreFeetPerAcre(fromMM:))
        let short = af.value - limit.value
        let head = short > 0.05 ? "Short by about \(Units.oneDecimal(short)) acre-feet per acre" : "Fits your limit in a typical year"
        var detail = "Needs \(Units.oneDecimal(af.value)) acre-ft/acre a year. Limit: \(Units.oneDecimal(limit.value))."
        if af.hasSpread { detail += " Likely \(Units.oneDecimal(af.low))–\(Units.oneDecimal(af.high))." }
        return Answer(id: "water", question: "Will the water limit cover irrigation?", headline: head, detail: detail, cite: cite,
                      tone: short > 0.05 ? .warn : .normal, status: example)
    }

    // MARK: Greenness

    static func greennessMeter(_ input: Input) -> Meter? {
        let st = stage(input)
        var v = st.ndvi, date = st.date
        if v == nil, input.isToday, let r = input.nasaNow?.reading("hls_ndvi") { v = r.value; date = GrowerDate.parse(r.obsDate) }
        guard let v else { return nil }
        return Meter(label: "Greenness", valueText: String(format: "%.2f", v), value: max(0, min(1, v)), reference: 0.6,
                     referenceLabel: "full canopy", scaleMax: 1, note: date.map { "0 to 1, \(GrowerDate.part($0))" } ?? "0 to 1")
    }

    // MARK: Soil and groundwater

    struct SoilGw { var soil: (value: Double, date: String?, smap: Bool)?; var groundwater: (value: Double, date: String?)? }

    static func soilAndGroundwater(_ input: Input) -> SoilGw {
        var out = SoilGw()
        if input.isToday, let now = input.nasaNow {
            if let r = now.reading("smap_rootzone_pct"), let v = r.value { out.soil = (v, r.obsDate, true) }
            else if let r = now.reading("grace_rootzone_pct"), let v = r.value { out.soil = (v, r.obsDate, false) }
            if let r = now.reading("grace_gw_pct"), let v = r.value { out.groundwater = (v, r.obsDate) }
        }
        if let daily = input.daily, out.soil == nil || out.groundwater == nil {
            let r = DailyAnalysis.readings(daily, at: input.t)
            if out.soil == nil, let s = r.soil { out.soil = (s.0, s.1, true) }
            if out.groundwater == nil, let g = r.groundwater { out.groundwater = (g.0, g.1) }
        }
        return out
    }

    static func band(_ v: Double, _ hi: String, _ mid: String, _ lo: String) -> String { v >= 67 ? hi : v > 33 ? mid : lo }

    static func soilAnswer(_ input: Input, _ sg: SoilGw) -> Answer {
        let soilHead = sg.soil.map { band($0.value, "Soil wetter than usual", "Soil about normal", "Soil drier than usual") } ?? "No soil reading"
        let gwHead = sg.groundwater.map { band($0.value, "more groundwater than usual", "groundwater about normal", "less groundwater than usual") } ?? "no groundwater reading"
        var detail = ""
        if let s = sg.soil {
            detail += "Soil moisture \(Units.ordinal(Int(s.value.rounded()))) percentile for the time of year"
            if let d = GrowerDate.parse(s.date), input.t.endDate.timeIntervalSince(d) > 20 * 86_400 { detail += " (latest, \(GrowerDate.part(d)))" }
            detail += "; 50 is normal. "
        }
        if let g = sg.groundwater {
            detail += "Groundwater \(Units.ordinal(Int(g.value.rounded()))) percentile"
            if let d = GrowerDate.parse(g.date), input.t.endDate.timeIntervalSince(d) > 20 * 86_400 { detail += " (latest, \(GrowerDate.part(d)))" }
            detail += ", whole basin, not your own well."
        }
        if detail.isEmpty { detail = "NASA soil and groundwater readings haven't loaded for this field." }
        let cite = sg.soil?.smap == false ? "NASA GRACE-FO with a land model, root zone and groundwater, one reading for a 17-mile square." : "NASA SMAP (soil, 6-mile square) and GRACE-FO (groundwater, weekly)."
        return Answer(id: "soil", question: "Is the soil wetter or drier than usual? And the groundwater?",
                      headline: "\(soilHead); \(gwHead)", detail: detail.trimmingCharacters(in: .whitespaces), cite: cite,
                      tone: (sg.groundwater?.value ?? 50) <= 20 ? .warn : .normal)
    }

    // MARK: The soil itself

    struct SoilFacts: Sendable, Equatable {
        var texture: String?
        var mix: SoilMix?
        var holds: String?
        var drains: String?
        var salt: String?
        var rotation: String?
        var source: String
        var line: String { [holds, drains, salt].compactMap { $0 }.joined(separator: " ") }
    }

    private static func known(_ s: String?) -> String? {
        guard let s, !s.isEmpty, !["unknown", "not fetched", "n/a"].contains(where: { s.lowercased().contains($0) }) else { return nil }
        return s
    }

    /// Ported from shared.tsx soilFacts().
    static func soilFacts(_ field: FieldLocation) -> SoilFacts? {
        guard let s = field.soil else { return nil }
        let texture = known(s.textureClass).map { $0.prefix(1).uppercased() + $0.dropFirst().lowercased() }
        let inFt = s.awcMmPerM?.value.map { $0 / 1000 * 12 }
        let dc = known(s.drainageClass)?.lowercased() ?? "", hg = known(s.hydrologicGroup).map { String($0.uppercased().prefix(1)) } ?? ""
        enum Drain { case slow, fast, well }
        let drain: Drain? = dc.isEmpty && hg.isEmpty ? nil : (hg == "D" || dc.contains("poorly") || dc.contains("imperfectly")) ? .slow : (dc.contains("excessive") || hg == "A") ? .fast : .well
        let ec = s.ecDsPerM, salty = (ec ?? 0) >= 4
        let tl = texture?.lowercased() ?? ""
        let clayey = (s.mix.map { $0.clay >= 35 } ?? false) || (tl.contains("clay") && !tl.contains("sandy clay loam"))
        let sandy = s.mix.map { $0.sand >= 60 } ?? tl.contains("sand")
        let rotation: String? = salty ? "Salt hurts some crops more than others; check the crop's salt tolerance with your adviser."
            : clayey && (hg == "C" || hg == "D") && drain == .slow ? "Clay holds water and drains slowly, so it suits flooded rice; slow drainage limits how much a rotation can improve infiltration."
            : sandy && (inFt ?? 9) < 1.4 ? "Sandy soil holds little water, so crops that need steady moisture take more irrigation here, and flooded rice would lose water downward."
            : nil
        let id = (s.sourceID ?? "").lowercased()
        let source = id.contains("aafc") || id.contains("slc") ? "AAFC Soil Landscapes of Canada v3.2, a 1:1,000,000 map (not field scale)"
            : id.contains("soilgrids") ? "SoilGrids global soil model (ISRIC), 800 ft squares"
            : field.isBC ? "Soil survey" : "USDA soil survey (SSURGO), top 3 feet"
        let f = SoilFacts(texture: texture, mix: s.mix,
                          holds: inFt.map { "Holds \(Units.oneDecimal($0)) in of water per foot.\($0 < 1.4 ? " Low." : "")" },
                          drains: drain.map { $0 == .slow ? "Drains slowly." : $0 == .fast ? "Drains fast." : "Drains well." },
                          salt: ec.map { $0 >= 4 ? "Salty: \(String(format: "%.1f", $0)) dS/m." : "Salt is low." },
                          rotation: rotation, source: source)
        return f.texture == nil && f.mix == nil && f.line.isEmpty ? nil : f
    }

    static func soilKindAnswer(_ field: FieldLocation) -> Answer? {
        guard let f = soilFacts(field) else { return nil }
        return Answer(id: "soil-kind", question: "What is the soil like?", headline: f.texture ?? "Soil", detail: f.line, cite: "\(f.source).")
    }

    // MARK: Adviser detail: crop stress and standing water, heat and frost

    static let driverWords = ["z_tmax": "unusual heat", "z_eto": "very thirsty air", "z_ndvi": "weaker growth than in its other years",
                              "iforest": "an unusual mix of heat, dryness and growth"]

    static func stressAnswer(_ input: Input) -> Answer? {
        var head: String?, detail = ""
        if let weeks = input.stress?.weeks, !weeks.isEmpty {
            let years = Set(weeks.compactMap(\.isoYear)).filter { $0 <= input.t.year }
            if let y = years.max() {
                let flagged = weeks.filter { $0.isoYear == y && ($0.flagZscore || $0.flagIforest) }
                var why: [String: Int] = [:]
                flagged.flatMap(\.drivers).forEach { why[$0, default: 0] += 1 }
                let top = why.max { $0.value < $1.value }?.key
                head = flagged.isEmpty ? "No crop-stress weeks in the \(y) season"
                    : "\(flagged.count) crop-stress week\(flagged.count == 1 ? "" : "s") in the \(y) season" + (top.map { ", mostly \(driverWords[$0] ?? "unusual weather")" } ?? "")
            }
        }
        if let w = input.waterSeen?.summary { detail = w }
        guard head != nil || !detail.isEmpty else { return nil }
        return Answer(id: "stress", question: "Has the crop been stressed, or the field under water?", headline: head ?? "Standing water",
                      detail: detail, cite: "Crop stress: two statistical methods on greenness, NASA POWER heat and dryness, growing season only. Standing water: NASA OPERA, 100 ft squares, clear images only.",
                      detailOnly: true)
    }

    static func heatAnswer(_ input: Input) -> Answer? {
        guard let daily = input.daily, let h = DailyAnalysis.heatFrost(daily, at: input.t) else { return nil }
        let head = "\(h.hot) day\(h.hot == 1 ? "" : "s") at or above \(DailyAnalysis.hotF) °F \(h.period.current ? "so far this year" : "in \(h.period.label.replacingOccurrences(of: "last year, ", with: ""))")"
        let detail = "Normal for the same dates: \(h.hotNormal.map { String(Int($0.rounded())) } ?? "not known"). Frost nights (32 °F or lower), \(h.frostPeriod.label): \(h.frost); normal \(h.frostNormal.map { String(Int($0.rounded())) } ?? "not known")."
        return Answer(id: "heat", question: "How many hot days and frost nights?", headline: head, detail: detail,
                      cite: "\(stationsName(input.field)). NASA POWER is not used for heat here: it runs about 6 °F hot in summer against the stations.",
                      detailOnly: true)
    }
}
