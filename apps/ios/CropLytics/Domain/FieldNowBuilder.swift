import Foundation

/// "Your field now": a compact visual summary, then at most 4 one-sentence answers.
/// Pure function of the API data, ported from frontend/app/src/components/ui/FieldNow.tsx.
struct FieldNowPresentation: Sendable {
    struct Summary: Sendable {
        let stripYear: Int
        let strip: [CoverClass]
        let todayDekad: Int
        let stage: String
        let stageClass: CoverClass
        let rain: Meter?
        let water: Meter?
        let greenness: Meter?
        let soilPercentile: Double?
        let groundwaterPercentile: Double?
        let soilGroundwaterNote: String
    }
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
        var today: Date
    }

    static func build(_ input: Input) -> FieldNowPresentation {
        let year = GrowerDate.year(input.today)
        let todayDekad = GrowerDate.dekad(input.today)
        let strip = input.calendar?.classes(for: year) ?? Array(repeating: .noView, count: 36)
        let stage = stage(input)
        let rain = rainMeter(input.nasaNow)
        let water = waterMeter(input.strategies, limit: input.limit)
        let green = greennessMeter(input)
        let soil = soilReading(input.nasaNow)
        let gw = input.nasaNow?.reading("grace_gw_pct")
        var note = "50 is normal for the time of year"
        if let d = soil?.reading.obsDate ?? gw?.obsDate, let date = GrowerDate.parse(d) { note += "; latest \(GrowerDate.part(date))" }
        let summary = FieldNowPresentation.Summary(
            stripYear: year, strip: strip, todayDekad: todayDekad, stage: stage.text, stageClass: stage.cls,
            rain: rain, water: water, greenness: green,
            soilPercentile: soil?.reading.value, groundwaterPercentile: gw?.value, soilGroundwaterNote: note
        )
        var answers: [Answer] = [growingAnswer(input, stage: stage)]
        answers.append(rainAnswer(input.nasaNow))
        if let a = waterAnswer(input.strategies, limit: input.limit) { answers.append(a) }
        answers.append(soilAnswer(input.nasaNow))
        return FieldNowPresentation(summary: summary, answers: Array(answers.prefix(4)))
    }

    // MARK: Stage (what is on the field)

    struct Stage { let text: String; let sub: String; let cls: CoverClass; let date: Date? }

    static func stage(_ input: Input) -> Stage {
        let cutoff = input.today
        if let cal = input.calendar, let obs = cal.latestObservation(before: cutoff),
           input.today.timeIntervalSince(obs.date) < 45 * 86_400 {
            let y = GrowerDate.year(obs.date), d = GrowerDate.dekad(obs.date)
            let smoothed = cal.classes(for: y)[d]
            let cls = smoothed == .noView ? obs.cls : smoothed
            return describe(cls, dekad: d, greenUp: cal.greenUpDekad(y), harvest: cal.harvestDekad(y), date: obs.date)
        }
        if let r = input.nasaNow?.reading("hls_ndvi"), let v = r.value {
            let cls: CoverClass = v < 0.2 ? .bare : v < 0.35 ? .partial : .covered
            let date = GrowerDate.parse(r.obsDate)
            return describe(cls, dekad: date.map(GrowerDate.dekad) ?? GrowerDate.dekad(input.today), greenUp: nil, harvest: nil, date: date)
        }
        return Stage(text: "No clear satellite view lately", sub: "Clouds, or no image in the last 6 weeks.", cls: .noView, date: nil)
    }

    static func describe(_ cls: CoverClass, dekad d: Int, greenUp: Int?, harvest: Int?, date: Date?) -> Stage {
        switch cls {
        case .water:
            let winter = d >= 30 || d <= 5
            return Stage(text: "Under water", sub: winter ? "Flooded for the winter, as in most years." : "Standing water on the field.", cls: cls, date: date)
        case .covered:
            if let up = greenUp, d >= up, harvest.map({ d < $0 }) ?? true {
                return Stage(text: "Crop growing, green since \(dekadText(up))", sub: "", cls: cls, date: date)
            }
            return Stage(text: "Full green cover", sub: "", cls: cls, date: date)
        case .partial:
            return Stage(text: "Thin cover", sub: "Some green, less than a full crop: a young crop, regrowth after a cutting, stubble or weeds.", cls: cls, date: date)
        case .bare:
            if let h = harvest, d > h { return Stage(text: "Bare since harvest in \(dekadText(h))", sub: "", cls: cls, date: date) }
            return Stage(text: "Bare ground", sub: "", cls: cls, date: date)
        case .noView:
            return Stage(text: "No clear satellite view lately", sub: "Clouds, or no image in the last 6 weeks.", cls: cls, date: date)
        }
    }

    static func satelliteName(_ cal: FieldCalendar?) -> String {
        cal?.source == "hls" ? "NASA/USGS HLS satellites (Landsat and Sentinel-2, harmonised by NASA)" : "Landsat (NASA/USGS) and Sentinel-2 satellites"
    }

    static func growingAnswer(_ input: Input, stage: Stage) -> Answer {
        let year = GrowerDate.year(input.today)
        var detail: String
        if let crop = input.field.cropHistory[String(year)] {
            detail = "\(FieldNaming.cropName(crop)) on record for \(year)."
        } else if let latest = FieldNaming.latestCrop(input.field.cropHistory) {
            detail = "The \(year) crop map isn't out yet (USDA publishes it early \(year + 1)). \(latest.year): \(latest.crop.lowercased())."
        } else {
            detail = "No crop on record."
        }
        if !stage.sub.isEmpty { detail += " " + stage.sub }
        var cite = "\(satelliteName(input.calendar)), 100 ft squares; crop from the USDA Cropland Data Layer."
        if let d = stage.date {
            let days = Int(input.today.timeIntervalSince(d) / 86_400)
            let ago = days < 8 ? "" : days < 14 ? ", about a week ago" : ", about \(days / 7) weeks ago"
            cite += " Latest clear view \(GrowerDate.short(d))\(ago)."
        }
        return Answer(id: "growing", question: "What is growing, and how far along?", headline: stage.text, detail: detail, cite: cite)
    }

    // MARK: Rain

    struct RainSoFar { let inches: Double; let normal: Double; let pct: Double; let date: Date? }

    static func rainSoFar(_ now: NasaNow?) -> RainSoFar? {
        guard let r = now?.reading("imerg_wy_to_date_mm"), let mm = r.value,
              let n = now?.reading("imerg_wy_to_date_normal_mm")?.value, n > 0 else { return nil }
        return RainSoFar(inches: Units.inches(fromMM: mm), normal: Units.inches(fromMM: n), pct: mm / n * 100, date: GrowerDate.parse(r.obsDate))
    }

    static func rainMeter(_ now: NasaNow?) -> Meter? {
        guard let r = rainSoFar(now) else { return nil }
        return Meter(label: "Rain since 1 Oct", valueText: "\(Units.inchesText(r.inches)) in", value: r.inches,
                     reference: r.normal, referenceLabel: "normal", scaleMax: max(r.inches, r.normal) * 1.25,
                     note: "\(Int(r.pct.rounded()))% of normal (\(Units.inchesText(r.normal)) in)")
    }

    static func rainAnswer(_ now: NasaNow?) -> Answer {
        let cite = "NASA GPM IMERG satellite rain over the field (one reading for a 6-mile square); normal = the same dates in the 2001–2025 seasons."
        guard let r = rainSoFar(now) else {
            return Answer(id: "rain", question: "How much rain so far this season?", headline: "No rain reading yet", detail: "The satellite rain record for this season hasn't loaded.", cite: cite)
        }
        let head = r.pct >= 115 ? "So far wetter than normal" : r.pct <= 85 ? "So far drier than normal" : "So far about normal"
        let by = r.date.flatMap { GrowerDate.shortNoYear(iso($0)) } ?? "today"
        let detail = "\(Units.inchesText(r.inches)) inches since 1 Oct; normal by \(by) is \(Units.inchesText(r.normal)) inches (\(Int(r.pct.rounded()))% of normal)."
        return Answer(id: "rain", question: "How much rain so far this season?", headline: head, detail: detail, cite: cite)
    }

    // MARK: Water need vs limit

    static func baseline(_ strategies: [Strategy]?) -> Strategy? {
        strategies?.first(where: \.isBaseline) ?? strategies?.first
    }

    static func waterMeter(_ strategies: [Strategy]?, limit: WaterLimitStore.Limit) -> Meter? {
        guard let need = baseline(strategies)?.water.irrigationNeedMm.value else { return nil }
        let af = Units.acreFeetPerAcre(fromMM: need)
        return Meter(label: "Water need, a year", valueText: "\(Units.oneDecimal(af)) acre-ft/acre", value: af,
                     reference: limit.value, referenceLabel: "your limit", scaleMax: max(af, limit.value) * 1.2,
                     note: "limit \(Units.oneDecimal(limit.value))\(limit.isExample ? " (example)" : "")", warn: af > limit.value)
    }

    static func waterAnswer(_ strategies: [Strategy]?, limit: WaterLimitStore.Limit) -> Answer? {
        guard let base = baseline(strategies), let range = NumRange(base.water.irrigationNeedMm) else { return nil }
        let af = range.map(Units.acreFeetPerAcre(fromMM:))
        let short = af.value - limit.value
        let head = short > 0.05 ? "Short by about \(Units.oneDecimal(short)) acre-feet per acre" : "Fits your limit in a typical year"
        var detail = "Today's rotation needs about \(Units.oneDecimal(af.value)) acre-feet per acre a year"
        if af.hasSpread { detail += " (likely \(Units.oneDecimal(af.low))–\(Units.oneDecimal(af.high)))" }
        detail += "; your limit is \(Units.oneDecimal(limit.value))."
        if limit.isExample { detail += " That limit is an example: change it to yours on Compare." }
        return Answer(id: "water", question: "Will the water limit cover irrigation?", headline: head, detail: detail,
                      cite: "Rotation model with NASA POWER weather: crop water use minus rain, typical year 2015–2025.",
                      tone: short > 0.05 ? .warn : .normal)
    }

    // MARK: Greenness

    static func greennessMeter(_ input: Input) -> Meter? {
        var value: Double?, date: Date?
        if let r = input.nasaNow?.reading("hls_ndvi") { value = r.value; date = GrowerDate.parse(r.obsDate) }
        if value == nil, let obs = input.calendar?.latestObservation(before: input.today), let v = obs.ndvi { value = v; date = obs.date }
        guard let v = value else { return nil }
        let words = v >= 0.6 ? "full canopy" : v >= 0.35 ? "partly green" : v >= 0.2 ? "thin green cover" : "little or no green"
        return Meter(label: "Greenness", valueText: String(format: "%.2f", v), value: max(0, min(1, v)), reference: 0.6,
                     referenceLabel: "full canopy", scaleMax: 1,
                     note: "0 to 1, \(words)\(date.map { ", \(GrowerDate.shortNoYear(iso($0)) ?? "")" } ?? "")")
    }

    // MARK: Soil and groundwater

    static func soilReading(_ now: NasaNow?) -> (reading: NasaNow.Reading, isSMAP: Bool)? {
        if let r = now?.reading("smap_rootzone_pct") { return (r, true) }
        if let r = now?.reading("grace_rootzone_pct") { return (r, false) }
        return nil
    }

    static func band(_ v: Double, _ hi: String, _ mid: String, _ lo: String) -> String { v >= 67 ? hi : v > 33 ? mid : lo }

    static func soilAnswer(_ now: NasaNow?) -> Answer {
        let soil = soilReading(now)
        let gw = now?.reading("grace_gw_pct")
        let soilHead = soil?.reading.value.map { band($0, "Soil wetter than usual", "Soil about normal", "Soil drier than usual") } ?? "No soil reading"
        let gwHead = gw?.value.map { band($0, "more groundwater than usual", "groundwater about normal", "less groundwater than usual") } ?? "no groundwater reading"
        var detail = ""
        if let s = soil, let v = s.reading.value {
            detail += "Soil moisture \(Units.ordinal(Int(v.rounded()))) percentile for the time of year"
            if let d = GrowerDate.parse(s.reading.obsDate), (s.reading.staleSteps ?? 0) > 1 { detail += " (latest, \(GrowerDate.part(d)))" }
            detail += "; 50 is normal. "
        }
        if let g = gw, let v = g.value {
            detail += "Groundwater \(Units.ordinal(Int(v.rounded()))) percentile"
            if let d = GrowerDate.parse(g.obsDate), (g.staleSteps ?? 0) > 1 { detail += " (latest, \(GrowerDate.part(d)))" }
            detail += ", whole basin, not your own well."
        }
        if detail.isEmpty { detail = "NASA soil and groundwater readings haven't loaded for this field." }
        let soilCite = soil?.isSMAP == true
            ? "Soil: NASA SMAP satellite, one reading for a 6-mile square."
            : "Soil: NASA GRACE-FO with a land model, root zone, one reading for a 17-mile square (NASA SMAP readings still downloading)."
        return Answer(id: "soil", question: "Is the soil wetter or drier than usual? And the groundwater?",
                      headline: "\(soilHead); \(gwHead)", detail: detail.trimmingCharacters(in: .whitespaces),
                      cite: "\(soilCite) Groundwater: NASA GRACE-FO satellites, weekly.",
                      tone: (gw?.value ?? 50) <= 20 ? .warn : .normal)
    }

    private static func iso(_ d: Date) -> String {
        let c = GrowerDate.calendar.dateComponents([.year, .month, .day], from: d)
        return String(format: "%04d-%02d-%02d", c.year ?? 2026, c.month ?? 1, c.day ?? 1)
    }
}
