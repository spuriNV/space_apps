import Foundation

// MARK: - GET .../nasa_now

/// Today's NASA readings for the field: each `{value, step, obs_date, stale_steps}`.
struct NasaNow: Decodable, Sendable {
    let step: String?
    let readings: [String: Reading]
    let plainLanguage: [String]
    let latestByDataset: [String: String]

    struct Reading: Decodable, Sendable {
        let value: Double?
        let obsDate: String?
        let staleSteps: Int?
        enum CodingKeys: String, CodingKey {
            case value
            case obsDate = "obs_date"
            case staleSteps = "stale_steps"
        }
        init(value: Double?, obsDate: String?, staleSteps: Int? = 0) {
            self.value = value; self.obsDate = obsDate; self.staleSteps = staleSteps
        }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            value = (try? c.decodeIfPresent(LossyDouble.self, forKey: .value))?.value
            obsDate = try? c.decodeIfPresent(String.self, forKey: .obsDate)
            staleSteps = try? c.decodeIfPresent(Int.self, forKey: .staleSteps)
        }
    }

    enum CodingKeys: String, CodingKey {
        case step, readings
        case plainLanguage = "plain_language"
        case latestByDataset = "latest_by_dataset"
    }

    init(step: String?, readings: [String: Reading], plainLanguage: [String] = [], latestByDataset: [String: String] = [:]) {
        self.step = step; self.readings = readings; self.plainLanguage = plainLanguage; self.latestByDataset = latestByDataset
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        step = try? c.decodeIfPresent(String.self, forKey: .step)
        readings = (try? c.decodeIfPresent([String: Reading].self, forKey: .readings)) ?? [:]
        plainLanguage = (try? c.decodeIfPresent([String].self, forKey: .plainLanguage)) ?? []
        latestByDataset = (try? c.decodeIfPresent([String: String].self, forKey: .latestByDataset)) ?? [:]
    }

    func reading(_ key: String) -> Reading? {
        guard let r = readings[key], r.value != nil else { return nil }
        return r
    }
}

// MARK: - GET .../calendar?source=hls

/// The field's satellite calendar: bare / partial / covered / water segments per year.
struct FieldCalendar: Decodable, Sendable {
    let source: String?
    let lastObservation: String?
    let years: [Year]

    struct Year: Decodable, Sendable {
        let year: Int
        let segments: [Segment]
        let markers: [Marker]
        let observations: [Observation]
        init(year: Int, segments: [Segment], markers: [Marker] = [], observations: [Observation] = []) {
            self.year = year; self.segments = segments; self.markers = markers; self.observations = observations
        }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            year = try c.decode(Int.self, forKey: .year)
            segments = (try? c.decodeIfPresent([Segment].self, forKey: .segments)) ?? []
            markers = (try? c.decodeIfPresent([Marker].self, forKey: .markers)) ?? []
            observations = (try? c.decodeIfPresent([Observation].self, forKey: .observations)) ?? []
        }
        enum CodingKeys: String, CodingKey { case year, segments, markers, observations }
    }

    struct Segment: Decodable, Sendable {
        let startDoy: Int
        let endDoy: Int
        let cls: String
        enum CodingKeys: String, CodingKey {
            case startDoy = "start_doy"
            case endDoy = "end_doy"
            case cls = "class"
        }
    }

    struct Marker: Decodable, Sendable {
        let date: String
        let type: String
    }

    struct Observation: Decodable, Sendable {
        let date: String
        let ndvi: Double?
        let cls: String?
        enum CodingKeys: String, CodingKey {
            case date, ndvi
            case cls = "class"
        }
    }

    enum CodingKeys: String, CodingKey {
        case source, years
        case lastObservation = "last_observation"
    }

    init(source: String?, lastObservation: String?, years: [Year]) {
        self.source = source; self.lastObservation = lastObservation; self.years = years
    }
}

// MARK: - GET .../strategies and POST .../score

/// One rotation scored by the engine (schemas/rotation_strategy.schema.json).
struct Strategy: Decodable, Sendable, Identifiable {
    let id: String
    let name: String
    let isBaseline: Bool
    let cycleYears: Int?
    let calendar: [CalendarEntry]
    let water: Water
    let exposure: Exposure
    let scores: [String: SourcedNumber]
    let composite: Composite?
    let brief: Brief?
    let filteredOut: Bool
    /// The API's own short name ("Rice + winter flood").
    var shortName: String? = nil

    /// Dryland rotation: no calendar year is irrigated (e.g. BC sainfoin-grass).
    var isRainFed: Bool { !calendar.isEmpty && calendar.allSatisfy { $0.irrigated == false } }

    struct CalendarEntry: Decodable, Sendable {
        let year: Int
        let cropId: String
        let plant: String
        let harvest: String
        let role: String?
        var irrigated: Bool? = nil
        enum CodingKeys: String, CodingKey {
            case year, plant, harvest, role, irrigated
            case cropId = "crop_id"
        }
    }

    struct Water: Decodable, Sendable {
        let irrigationNeedMm: SourcedNumber
        let etcVsOpenetPct: SourcedNumber?
        let allocationStatus: String?
        enum CodingKeys: String, CodingKey {
            case irrigationNeedMm = "irrigation_need_mm"
            case etcVsOpenetPct = "etc_vs_openet_pct"
            case allocationCheck = "allocation_check"
        }
        private struct AllocationCheck: Decodable { let status: String? }
        init(irrigationNeedMm: SourcedNumber, etcVsOpenetPct: SourcedNumber? = nil, allocationStatus: String? = nil) {
            self.irrigationNeedMm = irrigationNeedMm; self.etcVsOpenetPct = etcVsOpenetPct; self.allocationStatus = allocationStatus
        }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            irrigationNeedMm = try c.decode(SourcedNumber.self, forKey: .irrigationNeedMm)
            etcVsOpenetPct = try? c.decodeIfPresent(SourcedNumber.self, forKey: .etcVsOpenetPct)
            allocationStatus = (try? c.decodeIfPresent(AllocationCheck.self, forKey: .allocationCheck))?.status
        }
    }

    struct Exposure: Decodable, Sendable {
        let bareDaysPerYear: SourcedNumber?
        let exposedRainDays: SourcedNumber?
        let replay: [String: Replay]
        struct Replay: Decodable, Sendable {
            let irrigationNeedMm: SourcedNumber?
            let exposedRainDays: SourcedNumber?
            enum CodingKeys: String, CodingKey {
                case irrigationNeedMm = "irrigation_need_mm"
                case exposedRainDays = "exposed_rain_days"
            }
        }
        enum CodingKeys: String, CodingKey {
            case replay
            case bareDaysPerYear = "bare_days_per_year"
            case exposedRainDays = "exposed_rain_days"
        }
        init(bareDaysPerYear: SourcedNumber?, exposedRainDays: SourcedNumber?, replay: [String: Replay] = [:]) {
            self.bareDaysPerYear = bareDaysPerYear; self.exposedRainDays = exposedRainDays; self.replay = replay
        }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            bareDaysPerYear = try? c.decodeIfPresent(SourcedNumber.self, forKey: .bareDaysPerYear)
            exposedRainDays = try? c.decodeIfPresent(SourcedNumber.self, forKey: .exposedRainDays)
            replay = (try? c.decodeIfPresent([String: Replay].self, forKey: .replay)) ?? [:]
        }
    }

    struct Composite: Decodable, Sendable {
        let value: Double?
        let low: Double?
        let high: Double?
        let rank: Int?
    }

    struct Brief: Decodable, Sendable {
        let localReview: [ReviewItem]
        let gaps: [Gap]
        struct ReviewItem: Decodable, Sendable { let item: String; let severity: String? }
        struct Gap: Decodable, Sendable { let text: String }
        enum CodingKeys: String, CodingKey {
            case gaps
            case localReview = "local_review"
        }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            localReview = (try? c.decodeIfPresent([ReviewItem].self, forKey: .localReview)) ?? []
            gaps = (try? c.decodeIfPresent([Gap].self, forKey: .gaps)) ?? []
        }
    }

    enum CodingKeys: String, CodingKey {
        case id, name, calendar, water, exposure, scores, composite, brief
        case isBaseline = "is_baseline"
        case cycleYears = "cycle_years"
        case filteredOut = "filtered_out"
        case shortName = "short_name"
    }

    init(id: String, name: String, isBaseline: Bool, cycleYears: Int? = 1, calendar: [CalendarEntry] = [], water: Water,
         exposure: Exposure, scores: [String: SourcedNumber] = [:], composite: Composite? = nil, brief: Brief? = nil, filteredOut: Bool = false) {
        self.id = id; self.name = name; self.isBaseline = isBaseline; self.cycleYears = cycleYears; self.calendar = calendar
        self.water = water; self.exposure = exposure; self.scores = scores; self.composite = composite; self.brief = brief
        self.filteredOut = filteredOut
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        name = try c.decode(String.self, forKey: .name)
        isBaseline = (try? c.decodeIfPresent(Bool.self, forKey: .isBaseline)) ?? false
        cycleYears = try? c.decodeIfPresent(Int.self, forKey: .cycleYears)
        calendar = (try? c.decodeIfPresent([CalendarEntry].self, forKey: .calendar)) ?? []
        water = try c.decode(Water.self, forKey: .water)
        exposure = (try? c.decodeIfPresent(Exposure.self, forKey: .exposure)) ?? Exposure(bareDaysPerYear: nil, exposedRainDays: nil)
        scores = (try? c.decodeIfPresent([String: SourcedNumber].self, forKey: .scores)) ?? [:]
        composite = try? c.decodeIfPresent(Composite.self, forKey: .composite)
        brief = try? c.decodeIfPresent(Brief.self, forKey: .brief)
        filteredOut = (try? c.decodeIfPresent(Bool.self, forKey: .filteredOut)) ?? false
        shortName = try? c.decodeIfPresent(String.self, forKey: .shortName)
    }
}

struct StrategyList: Decodable, Sendable {
    let items: [Strategy]
}

/// POST /api/locations/{id}/score request body: the water limit, the grower's priorities (0-4) and a what-if.
struct ScoreRequest: Encodable, Sendable, Equatable {
    let allocation: Double
    var weights: [String: Int]? = nil
    var scenario: Scenario? = nil

    struct Scenario: Encodable, Sendable, Equatable {
        var dT_c: Double
        var dP_pct: Double
    }
}

// MARK: - GET .../models (machine-learning comparison)

struct ModelReport: Decodable, Sendable {
    let items: [Item]
    struct Item: Decodable, Sendable, Identifiable {
        let id: String
        let task: String
        let method: String
        let metrics: [String: Double]
        let notes: String?
        enum CodingKeys: String, CodingKey { case id, task, method, metrics, notes }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            id = try c.decode(String.self, forKey: .id)
            task = (try? c.decode(String.self, forKey: .task)) ?? ""
            method = (try? c.decode(String.self, forKey: .method)) ?? ""
            let raw = (try? c.decodeIfPresent([String: LossyDouble].self, forKey: .metrics)) ?? [:]
            metrics = raw.compactMapValues { $0.value }
            notes = try? c.decodeIfPresent(String.self, forKey: .notes)
        }
    }
}

// MARK: - GET /api/glossary

struct Glossary: Decodable, Sendable {
    let items: [Entry]
    struct Entry: Decodable, Sendable, Identifiable {
        let id: String
        let term: String
        let short: String
    }
}

// MARK: - GET .../stress (not on every deploy yet)

struct StressReport: Decodable, Sendable {
    let weeks: [Week]
    struct Week: Decodable, Sendable {
        let weekStart: String?
        let isoYear: Int?
        let crop: String?
        let flagZscore: Bool
        let flagIforest: Bool
        let drivers: [String]
        enum CodingKeys: String, CodingKey {
            case crop, drivers
            case weekStart = "week_start"
            case isoYear = "iso_year"
            case flagZscore = "flag_zscore"
            case flagIforest = "flag_iforest"
        }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            weekStart = try? c.decodeIfPresent(String.self, forKey: .weekStart)
            isoYear = try? c.decodeIfPresent(Int.self, forKey: .isoYear)
            crop = try? c.decodeIfPresent(String.self, forKey: .crop)
            flagZscore = (try? c.decodeIfPresent(Bool.self, forKey: .flagZscore)) ?? false
            flagIforest = (try? c.decodeIfPresent(Bool.self, forKey: .flagIforest)) ?? false
            drivers = (try? c.decodeIfPresent([String].self, forKey: .drivers)) ?? []
        }
    }
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        weeks = (try? c.decodeIfPresent([Week].self, forKey: .weeks)) ?? []
    }
    enum CodingKeys: String, CodingKey { case weeks }
}

// MARK: - GET .../water_seen (NASA OPERA standing water)

struct WaterSeen: Decodable, Sendable {
    let summary: String?
    let scenes: [Scene]
    struct Scene: Decodable, Sendable {
        let date: String
        let waterFrac: Double?
        enum CodingKeys: String, CodingKey { case date; case waterFrac = "water_frac" }
    }
    enum CodingKeys: String, CodingKey { case summary, scenes }
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        summary = try? c.decodeIfPresent(String.self, forKey: .summary)
        scenes = (try? c.decodeIfPresent([Scene].self, forKey: .scenes)) ?? []
    }
}

// MARK: - GET .../insurance (USDA RMA, county level)

struct InsuranceProfile: Decodable, Sendable {
    let profiles: [String: Profile]
    struct Profile: Decodable, Sendable {
        let scope: String?
        let crop: String?
        let totalIndemnityUsd: Double?
        enum CodingKeys: String, CodingKey {
            case scope, crop
            case totalIndemnityUsd = "total_indemnity_usd"
        }
    }
    let years: [Int]
    enum CodingKeys: String, CodingKey { case profiles, years }
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        profiles = (try? c.decodeIfPresent([String: Profile].self, forKey: .profiles)) ?? [:]
        years = (try? c.decodeIfPresent([Int].self, forKey: .years)) ?? []
    }
}
