import Foundation
import CoreLocation

// MARK: - GET .../daily?from=2016-01-01 (only the columns the app reads)

/// The daily weather and NASA record: rain (NASA IMERG, else stations), station highs and lows, soil and groundwater percentiles.
struct DailyRecord: Decodable, Sendable {
    let rows: [Row]

    struct Row: Decodable, Sendable {
        let date: String
        let imergMm: Double?
        let stationMm: Double?
        let tmaxC: Double?
        let tminC: Double?
        let smapPct: Double?
        let gracePct: Double?
        /// Rain: NASA GPM IMERG over the field when present, else the station mean.
        var rainMm: Double? { imergMm ?? stationMm }

        enum CodingKeys: String, CodingKey {
            case date
            case imergMm = "imerg_precip_mm"
            case stationMm = "ncei_precip_mm"
            case tmaxC = "ncei_tmax_c"
            case tminC = "ncei_tmin_c"
            case smapPct = "smap_sm_pct"
            case gracePct = "grace_gw_pct"
        }
        init(date: String, imergMm: Double? = nil, stationMm: Double? = nil, tmaxC: Double? = nil, tminC: Double? = nil, smapPct: Double? = nil, gracePct: Double? = nil) {
            self.date = date; self.imergMm = imergMm; self.stationMm = stationMm; self.tmaxC = tmaxC; self.tminC = tminC
            self.smapPct = smapPct; self.gracePct = gracePct
        }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            date = try c.decode(String.self, forKey: .date)
            func d(_ k: CodingKeys) -> Double? { (try? c.decodeIfPresent(LossyDouble.self, forKey: k))?.value }
            imergMm = d(.imergMm); stationMm = d(.stationMm); tmaxC = d(.tmaxC); tminC = d(.tminC); smapPct = d(.smapPct); gracePct = d(.gracePct)
        }
    }

    init(rows: [Row]) { self.rows = rows }
    enum CodingKeys: String, CodingKey { case rows, items }
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        rows = (try? c.decodeIfPresent([Row].self, forKey: .rows)) ?? (try? c.decodeIfPresent([Row].self, forKey: .items)) ?? []
    }
}

// MARK: - GET .../calendar_ml (same shape as the calendar, plus how it compares)

struct MLCalendar: Decodable, Sendable {
    let calendar: FieldCalendar
    let detector: String?
    let disagreePct: Double?
    /// "estimate" for BC (a two-class rule standing in for the trained model).
    let source: String?

    enum CodingKeys: String, CodingKey {
        case detector
        case disagreePct = "disagreement_with_rule_obs_pct"
        case source = "_source"
    }
    init(from decoder: Decoder) throws {
        calendar = try FieldCalendar(from: decoder)
        let c = try decoder.container(keyedBy: CodingKeys.self)
        detector = try? c.decodeIfPresent(String.self, forKey: .detector)
        disagreePct = (try? c.decodeIfPresent(LossyDouble.self, forKey: .disagreePct))?.value
        source = try? c.decodeIfPresent(String.self, forKey: .source)
    }
}

// MARK: - GET .../first_nations (BC only)

struct FirstNationsDetail: Decodable, Sendable {
    let statement: String?
    let fieldOnReserve: Bool?
    let nearestKm: Double?
    let nearestNation: String?
    let lowerRiver: LowerRiver?
    let nearby: [Reserve]
    let engagementSteps: [String]
    let principles: [Principle]
    let contacts: [Contact]
    let waterTimeline: [TimelineItem]
    let notes: [String]

    struct LowerRiver: Decodable, Sendable { let nation: String; let url: String?; let reserve: String? }
    struct Reserve: Decodable, Sendable, Identifiable {
        let reserve: String
        let nation: String?
        let distanceKm: Double
        var id: String { reserve }
        enum CodingKeys: String, CodingKey { case reserve, nation; case distanceKm = "distance_to_field_km" }
    }
    struct Principle: Decodable, Sendable, Identifiable { let id: String; let name: String; let description: String?; let url: String? }
    struct Contact: Decodable, Sendable { let nation: String; let department: String?; let url: String? }
    struct TimelineItem: Decodable, Sendable { let date: String; let title: String; let url: String? }

    enum CodingKeys: String, CodingKey {
        case statement, nearby, principles, contacts, notes
        case fieldOnReserve = "field_on_reserve"
        case nearestKm = "nearest_km"
        case nearestNation = "nearest_nation"
        case lowerRiver = "lower_river_nation"
        case engagementSteps = "engagement_steps"
        case waterTimeline = "water_timeline"
    }
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        statement = try? c.decodeIfPresent(String.self, forKey: .statement)
        fieldOnReserve = try? c.decodeIfPresent(Bool.self, forKey: .fieldOnReserve)
        nearestKm = (try? c.decodeIfPresent(LossyDouble.self, forKey: .nearestKm))?.value
        nearestNation = try? c.decodeIfPresent(String.self, forKey: .nearestNation)
        lowerRiver = try? c.decodeIfPresent(LowerRiver.self, forKey: .lowerRiver)
        nearby = (try? c.decodeIfPresent([Reserve].self, forKey: .nearby)) ?? []
        engagementSteps = (try? c.decodeIfPresent([String].self, forKey: .engagementSteps)) ?? []
        principles = (try? c.decodeIfPresent([Principle].self, forKey: .principles)) ?? []
        contacts = (try? c.decodeIfPresent([Contact].self, forKey: .contacts)) ?? []
        waterTimeline = (try? c.decodeIfPresent([TimelineItem].self, forKey: .waterTimeline)) ?? []
        notes = (try? c.decodeIfPresent([String].self, forKey: .notes)) ?? []
    }
}

// MARK: - GET .../grid (30 m cells with quarterly greenness): the 3D drill-down

struct FieldGrid: Decodable, Sendable {
    let cells: [Cell]

    struct Cell: Sendable {
        let row: Int
        let col: Int
        let ring: [CLLocationCoordinate2D]
        let inField: Double
        /// "2025_q3" -> NDVI
        let ndvi: [String: Double]
    }

    private struct Feature: Decodable {
        let geometry: Geometry?
        let properties: [String: LossyDouble]
    }
    enum CodingKeys: String, CodingKey { case features }

    init(cells: [Cell]) { self.cells = cells }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let features = (try? c.decode([Feature].self, forKey: .features)) ?? []
        cells = features.compactMap { f in
            guard let ring = f.geometry?.rings.first, ring.count > 2 else { return nil }
            var ndvi: [String: Double] = [:]
            for (k, v) in f.properties where k.hasPrefix("ndvi_") { if let x = v.value { ndvi[String(k.dropFirst(5))] = x } }
            return Cell(row: Int(f.properties["row"]?.value ?? 0), col: Int(f.properties["col"]?.value ?? 0), ring: ring,
                        inField: f.properties["frac_in_field"]?.value ?? 1, ndvi: ndvi)
        }
    }
}

// MARK: - /iss/{id}/iss.json (static file next to the web app): astronaut photos near the field

struct ISSPhotos: Decodable, Sendable {
    let credit: String?
    let photos: [Photo]
    struct Photo: Decodable, Sendable {
        let photoID: String
        let date: String?
        let centerLat: Double?
        let centerLon: Double?
        let features: String?
        let pageURL: String?
        let file: String
        enum CodingKeys: String, CodingKey {
            case date, features, file
            case photoID = "photo_id"
            case centerLat = "center_lat"
            case centerLon = "center_lon"
            case pageURL = "page_url"
        }
    }
}

// MARK: - GET .../salmon (BC; shown once the route is published)

/// Read loosely: the route is not published yet, so any of these fields may be what arrives.
struct SalmonInfo: Decodable, Sendable {
    let title: String?
    let summary: String?
    let lines: [String]
    let items: [Item]
    struct Item: Decodable, Sendable, Identifiable {
        let date: String?
        let title: String
        let url: String?
        var id: String { (date ?? "") + title }
    }
    enum CodingKeys: String, CodingKey { case title, summary, plainLanguage = "plain_language", items, timeline, runs }
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        title = try? c.decodeIfPresent(String.self, forKey: .title)
        summary = try? c.decodeIfPresent(String.self, forKey: .summary)
        if let l = try? c.decodeIfPresent([String].self, forKey: .plainLanguage) { lines = l }
        else if let one = try? c.decodeIfPresent(String.self, forKey: .plainLanguage) { lines = [one] }
        else { lines = [] }
        items = (try? c.decodeIfPresent([Item].self, forKey: .items)) ?? (try? c.decodeIfPresent([Item].self, forKey: .timeline)) ?? (try? c.decodeIfPresent([Item].self, forKey: .runs)) ?? []
    }
    var isEmpty: Bool { summary == nil && lines.isEmpty && items.isEmpty }
}

// MARK: - GET .../first_nations/reserves.geojson (BC map layer, context only)

struct ReserveOutlines: Decodable, Sendable {
    let outlines: [Outline]
    struct Outline: Sendable, Identifiable {
        let id: String
        let name: String
        let rings: [[CLLocationCoordinate2D]]
    }
    private struct Feature: Decodable {
        let geometry: Geometry?
        let properties: [String: LossyString]?
    }
    enum CodingKeys: String, CodingKey { case features }
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let fs = (try? c.decode([Feature].self, forKey: .features)) ?? []
        outlines = fs.enumerated().compactMap { i, f in
            guard let g = f.geometry, !g.rings.isEmpty else { return nil }
            let name = f.properties?["ENGLISH_NAME"]?.value ?? f.properties?["name"]?.value ?? f.properties?["reserve"]?.value ?? "Reserve"
            return Outline(id: "\(i)-\(name)", name: name, rings: g.rings)
        }
    }
}
