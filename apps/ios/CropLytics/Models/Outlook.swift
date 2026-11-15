import Foundation

/// GET /api/locations/{id}/outlook (backend/outlook): the coming-season file.
/// Outlooks, not forecasts. Only the parts the app shows are decoded.
struct Outlook: Decodable, Sendable {
    let county: String?
    let today: String?
    let comingSeason: String?
    let cpc: CPC?
    let drought: Drought?
    let reservoirs: [Reservoir]
    let snow: Snow?
    let allocations: Allocations?
    let field: FieldExpectations?
    let irrigation: Irrigation?
    let plainLanguageSummary: String?
    let notYetPublished: [Pending]

    struct CPC: Decodable, Sendable {
        let issued: String?
        let nextIssue: String?
        let seasons: [Season]
        enum CodingKeys: String, CodingKey {
            case issued, seasons
            case nextIssue = "next_issue"
        }
    }

    struct Season: Decodable, Sendable, Identifiable {
        let season: String
        let lead: Int?
        let temperature: Category?
        let precipitation: Category?
        var id: String { season }
    }

    struct Category: Decodable, Sendable {
        let category: String
        let probability: SourcedNumber?
        var isAbove: Bool { category.hasPrefix("above") }
        var isBelow: Bool { category.hasPrefix("below") }
    }

    struct Drought: Decodable, Sendable {
        let monitor: Monitor?
        let outlook: DroughtOutlook?
        struct Monitor: Decodable, Sendable {
            let county: String?
            let mapDate: String?
            let worstCategory: String?
            let worstCategoryCode: String?
            enum CodingKeys: String, CodingKey {
                case county
                case mapDate = "map_date"
                case worstCategory = "worst_category"
                case worstCategoryCode = "worst_category_code"
            }
        }
        struct DroughtOutlook: Decodable, Sendable {
            let seasonal: Item?
            struct Item: Decodable, Sendable { let category: String?; let target: String? }
        }
        enum CodingKeys: String, CodingKey {
            case monitor = "us_drought_monitor"
            case outlook = "cpc_drought_outlook"
        }
    }

    struct Reservoir: Decodable, Sendable, Identifiable {
        var id: String = ""
        let name: String
        let latestDate: String?
        let storageAf: SourcedNumber?
        let capacityAf: SourcedNumber?
        let pctOfCapacity: SourcedNumber?
        let pctOfAverage: SourcedNumber?
        let storageYearAgoAf: SourcedNumber?
        enum CodingKeys: String, CodingKey {
            case name
            case latestDate = "latest_daily_date"
            case storageAf = "storage_af"
            case capacityAf = "capacity_af"
            case pctOfCapacity = "pct_of_capacity"
            case pctOfAverage = "pct_of_cdec_average"
            case storageYearAgoAf = "storage_year_ago_af"
        }
    }

    struct Snow: Decodable, Sendable {
        let statewide: Statewide?
        let bulletin120: B120?
        struct Statewide: Decodable, Sendable {
            let reportDate: String?
            let sweInches: SourcedNumber?
            enum CodingKeys: String, CodingKey {
                case reportDate = "report_date"
                case sweInches = "swe_inches"
            }
        }
        struct B120: Decodable, Sendable { let status: String? }
        enum CodingKeys: String, CodingKey {
            case statewide = "snow_now_statewide"
            case bulletin120 = "bulletin_120"
        }
    }

    struct Allocations: Decodable, Sendable {
        let cvp: CVP?
        let history: History?
        struct CVP: Decodable, Sendable {
            let current: Current?
            struct Current: Decodable, Sendable {
                let settlement: SourcedNumber?
                let northAg: SourcedNumber?
                let southAg: SourcedNumber?
                enum CodingKeys: String, CodingKey {
                    case settlement = "sacramento_river_settlement_contractors"
                    case northAg = "north_of_delta_ag"
                    case southAg = "south_of_delta_ag"
                }
            }
            enum CodingKeys: String, CodingKey { case current = "wy2026" }
        }
        struct History: Decodable, Sendable {
            let rows: [Row]
            struct Row: Decodable, Sendable, Identifiable {
                let allocationYear: Int
                let pctOfCapacity: Double?
                let southAg: Double?
                let settlement: Double?
                let partialYear: Bool?
                var id: Int { allocationYear }
                enum CodingKeys: String, CodingKey {
                    case allocationYear = "allocation_year"
                    case pctOfCapacity = "pct_of_capacity"
                    case southAg = "cvp_south_of_delta_ag_pct"
                    case settlement = "cvp_settlement_contractors_pct"
                    case partialYear = "partial_year"
                }
            }
        }
        enum CodingKeys: String, CodingKey {
            case cvp
            case history = "storage_vs_final_allocation"
        }
    }

    struct FieldExpectations: Decodable, Sendable {
        let currentCrop: String?
        let bareWindow: BareWindow?
        let heavyRain: HeavyRain?
        struct BareWindow: Decodable, Sendable {
            let medianStart: String?
            let medianEnd: String?
            let medianDays: SourcedNumber?
            let note: String?
            enum CodingKeys: String, CodingKey {
                case note
                case medianStart = "median_start"
                case medianEnd = "median_end"
                case medianDays = "median_days"
            }
        }
        struct HeavyRain: Decodable, Sendable {
            let climatology: SourcedNumber?
            let givenOutlook: SourcedNumber?
            enum CodingKeys: String, CodingKey {
                case climatology = "chance_any_day_ge_25mm_climatology"
                case givenOutlook = "chance_given_cpc_outlook"
            }
        }
        enum CodingKeys: String, CodingKey {
            case currentCrop = "current_crop"
            case bareWindow = "bare_window"
            case heavyRain = "heavy_rain_in_window"
        }
    }

    struct Irrigation: Decodable, Sendable {
        let strategies: [Item]
        struct Item: Decodable, Sendable, Identifiable {
            let id: String
            let name: String?
            let isBaseline: Bool?
            let need: SourcedNumber?
            enum CodingKeys: String, CodingKey {
                case id, name
                case isBaseline = "is_baseline"
                case need = "irrigation_need_af_ac"
            }
        }
    }

    struct Pending: Decodable, Sendable {
        let item: String
        let status: String?
    }

    enum CodingKeys: String, CodingKey {
        case county, today, drought
        case comingSeason = "coming_season"
        case cpc = "cpc_seasonal_outlook"
        case reservoirs = "reservoirs_now"
        case snow = "snowpack_runoff"
        case allocations = "allocations_context"
        case field = "field_expectations_from_history"
        case irrigation = "irrigation_2027"
        case plainLanguageSummary = "plain_language_summary"
        case notYetPublished = "blocked_or_not_yet_published"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        county = try? c.decodeIfPresent(String.self, forKey: .county)
        today = try? c.decodeIfPresent(String.self, forKey: .today)
        comingSeason = try? c.decodeIfPresent(String.self, forKey: .comingSeason)
        cpc = try? c.decodeIfPresent(CPC.self, forKey: .cpc)
        drought = try? c.decodeIfPresent(Drought.self, forKey: .drought)
        let res = (try? c.decodeIfPresent([String: Reservoir].self, forKey: .reservoirs)) ?? [:]
        reservoirs = res.map { key, value in var r = value; r.id = key; return r }
            .sorted { ($0.capacityAf?.value ?? 0) > ($1.capacityAf?.value ?? 0) }
        snow = try? c.decodeIfPresent(Snow.self, forKey: .snow)
        allocations = try? c.decodeIfPresent(Allocations.self, forKey: .allocations)
        field = try? c.decodeIfPresent(FieldExpectations.self, forKey: .field)
        irrigation = try? c.decodeIfPresent(Irrigation.self, forKey: .irrigation)
        plainLanguageSummary = try? c.decodeIfPresent(String.self, forKey: .plainLanguageSummary)
        notYetPublished = (try? c.decodeIfPresent([Pending].self, forKey: .notYetPublished)) ?? []
    }
}
