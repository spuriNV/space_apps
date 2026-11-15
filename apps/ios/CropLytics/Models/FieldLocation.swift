import Foundation
import CoreLocation

/// GET /api/locations and /api/locations/{id} (schemas/location.schema.json).
/// Only the parts the app shows are decoded; everything else in the payload is ignored.
struct FieldLocation: Decodable, Identifiable, Sendable {
    let id: String
    let name: String?
    let countyFips: String?
    let centroid: Coordinate
    let geometry: Geometry?
    let areaHa: SourcedNumber?
    let soil: Soil?
    let terrain: Terrain?
    let water: Water?
    let cropHistory: [String: String]
    let nasaDatasets: [NasaDataset]
    let dwrUniqueId: String?
    let events: [FieldEvent]
    /// Optional fields the backend is adding with the 14-field registry (backend/fields/registry.json).
    let farmerName: String?
    let countyName: String?
    let acresValue: Double?
    /// "ca" or "bc".
    let region: String
    /// "rice", "forage" (else from the id).
    let family: String
    /// BC: the watershed and the irrigation orders, in place of a California water district.
    let waterContext: WaterContext?
    /// BC: the First Nations summary; the full card comes from GET .../first_nations.
    let firstNations: FirstNationsSummary?
    /// BC: California datasets this field lacks, with the reason.
    let dataGaps: [DataGap]
    /// The example water limit the API suggests (acre-ft/acre), until the grower sets one.
    let exampleLimit: Double?

    var isBC: Bool { region == "bc" }

    struct WaterContext: Decodable, Sendable {
        let watershed: String?
        let orders: [WaterOrder]
        let note: String?
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            watershed = try? c.decodeIfPresent(String.self, forKey: .watershed)
            orders = (try? c.decodeIfPresent([WaterOrder].self, forKey: .orders)) ?? []
            note = try? c.decodeIfPresent(String.self, forKey: .note)
        }
        enum CodingKeys: String, CodingKey { case watershed, orders, note }
    }

    struct WaterOrder: Decodable, Sendable, Identifiable {
        let date: String
        let kind: String?
        let title: String
        let url: String?
        var id: String { date + title }
    }

    struct FirstNationsSummary: Decodable, Sendable {
        let statement: String?
        let fieldOnReserve: Bool?
        let nearestKm: Double?
        let nearestNation: String?
        let lowerRiverNation: String?
        enum CodingKeys: String, CodingKey {
            case statement
            case fieldOnReserve = "field_on_reserve"
            case nearestKm = "nearest_km"
            case nearestNation = "nearest_nation"
            case lowerRiverNation = "lower_river_nation"
        }
    }

    struct DataGap: Decodable, Sendable, Identifiable {
        let id: String
        let what: String?
        let reason: String?
    }

    func gap(_ id: String) -> DataGap? { isBC ? dataGaps.first { $0.id == id } : nil }

    struct Coordinate: Decodable, Sendable, Equatable {
        let lat: Double
        let lon: Double
        var clCoordinate: CLLocationCoordinate2D { .init(latitude: lat, longitude: lon) }
    }

    struct Soil: Decodable, Sendable {
        let muname: String?
        let drainageClass: String?
        let hydrologicGroup: String?
        let textureClass: String?
        let ecDsPerM: Double?
        let awcMmPerM: SourcedNumber?
        let omPct: SourcedNumber?
        let mix: SoilMix?
        let sourceID: String?

        enum CodingKeys: String, CodingKey {
            case muname
            case drainageClass = "drainage_class"
            case hydrologicGroup = "hydrologic_group"
            case textureClass = "texture_class"
            case ecDsPerM = "ec_ds_per_m"
            case awcMmPerM = "awc_mm_per_m"
            case omPct = "om_pct"
            case textureDetail = "texture_detail"
            case source
        }
        private struct TextureDetail: Decodable {
            let sand: Double?, silt: Double?, clay: Double?
            enum CodingKeys: String, CodingKey { case sand = "sand_pct", silt = "silt_pct", clay = "clay_pct" }
            init(from decoder: Decoder) throws {
                let c = try decoder.container(keyedBy: CodingKeys.self)
                sand = (try? c.decodeIfPresent(LossyDouble.self, forKey: .sand))?.value
                silt = (try? c.decodeIfPresent(LossyDouble.self, forKey: .silt))?.value
                clay = (try? c.decodeIfPresent(LossyDouble.self, forKey: .clay))?.value
            }
        }
        private struct SourceRef: Decodable { let id: String? }

        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            muname = try? c.decodeIfPresent(String.self, forKey: .muname)
            drainageClass = try? c.decodeIfPresent(String.self, forKey: .drainageClass)
            hydrologicGroup = try? c.decodeIfPresent(String.self, forKey: .hydrologicGroup)
            textureClass = try? c.decodeIfPresent(String.self, forKey: .textureClass)
            ecDsPerM = (try? c.decodeIfPresent(LossyDouble.self, forKey: .ecDsPerM))?.value
            awcMmPerM = try? c.decodeIfPresent(SourcedNumber.self, forKey: .awcMmPerM)
            omPct = try? c.decodeIfPresent(SourcedNumber.self, forKey: .omPct)
            if let td = try? c.decodeIfPresent(TextureDetail.self, forKey: .textureDetail), let a = td.sand, let b = td.silt, let d = td.clay {
                mix = SoilMix(sand: a, silt: b, clay: d)
            } else {
                mix = nil
            }
            sourceID = (try? c.decodeIfPresent(SourceRef.self, forKey: .source))?.id
        }
    }

    struct Terrain: Decodable, Sendable {
        let slopeMeanPct: SourcedNumber?
        let lowSpotFraction: SourcedNumber?
        enum CodingKeys: String, CodingKey {
            case slopeMeanPct = "slope_mean_pct"
            case lowSpotFraction = "low_spot_fraction"
        }
    }

    struct Water: Decodable, Sendable {
        let source: String?
        let district: String?
        let sgmaSubbasin: String?
        let sgmaStatus: String?
        let exampleLimit: SourcedNumber?
        enum CodingKeys: String, CodingKey {
            case source, district
            case sgmaSubbasin = "sgma_subbasin"
            case sgmaStatus = "sgma_status"
            case exampleLimit = "example_limit_af_ac"
        }
        private struct Status: Decodable { let text: String? }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            source = try? c.decodeIfPresent(String.self, forKey: .source)
            district = try? c.decodeIfPresent(String.self, forKey: .district)
            sgmaSubbasin = try? c.decodeIfPresent(String.self, forKey: .sgmaSubbasin)
            sgmaStatus = (try? c.decodeIfPresent(Status.self, forKey: .sgmaStatus))?.text
            exampleLimit = try? c.decodeIfPresent(SourcedNumber.self, forKey: .exampleLimit)
        }
        var isSurface: Bool { source == "surface" }
    }

    struct FieldEvent: Decodable, Sendable, Identifiable {
        let date: String
        let title: String
        let url: String?
        let type: String?
        let short: String?
        var id: String { date + title }
    }

    enum CodingKeys: String, CodingKey {
        case id, name, centroid, geometry, soil, terrain, water, events, county, acres
        case countyFips = "county_fips"
        case areaHa = "area_ha"
        case cropHistory = "crop_history"
        case nasaDatasets = "nasa_datasets"
        case dwrUniqueId = "dwr_unique_id"
        case farmerName = "farmer_name"
        case countyName = "county_name"
        case region, family
        case waterContext = "water_context"
        case firstNations = "first_nations"
        case dataGaps = "data_gaps"
    }

    private struct CountyObject: Decodable { let name: String? }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        name = try? c.decodeIfPresent(String.self, forKey: .name)
        countyFips = (try? c.decodeIfPresent(LossyString.self, forKey: .countyFips))?.value
        centroid = try c.decode(Coordinate.self, forKey: .centroid)
        geometry = try? c.decodeIfPresent(Geometry.self, forKey: .geometry)
        areaHa = try? c.decodeIfPresent(SourcedNumber.self, forKey: .areaHa)
        soil = try? c.decodeIfPresent(Soil.self, forKey: .soil)
        terrain = try? c.decodeIfPresent(Terrain.self, forKey: .terrain)
        water = try? c.decodeIfPresent(Water.self, forKey: .water)
        cropHistory = (try? c.decodeIfPresent([String: String].self, forKey: .cropHistory)) ?? [:]
        nasaDatasets = (try? c.decodeIfPresent([NasaDataset].self, forKey: .nasaDatasets)) ?? []
        dwrUniqueId = (try? c.decodeIfPresent(LossyString.self, forKey: .dwrUniqueId))?.value
        events = (try? c.decodeIfPresent([FieldEvent].self, forKey: .events)) ?? []
        farmerName = try? c.decodeIfPresent(String.self, forKey: .farmerName)
        // `county` may arrive as "Colusa" or {"fips": "06011", "name": "Colusa"}; `county_name` as a plain string.
        if let s = try? c.decodeIfPresent(String.self, forKey: .county) {
            countyName = s
        } else if let o = try? c.decodeIfPresent(CountyObject.self, forKey: .county), let n = o.name {
            countyName = n
        } else {
            countyName = try? c.decodeIfPresent(String.self, forKey: .countyName)
        }
        if let s = try? c.decodeIfPresent(SourcedNumber.self, forKey: .acres) {
            acresValue = s.value
        } else {
            acresValue = nil
        }
        region = (try? c.decodeIfPresent(String.self, forKey: .region)) ?? (id.hasPrefix("bc") ? "bc" : "ca")
        family = (try? c.decodeIfPresent(String.self, forKey: .family)) ?? (id.hasPrefix("car") ? "rice" : id.hasPrefix("caf") ? "forage" : "other")
        waterContext = try? c.decodeIfPresent(WaterContext.self, forKey: .waterContext)
        firstNations = try? c.decodeIfPresent(FirstNationsSummary.self, forKey: .firstNations)
        dataGaps = (try? c.decodeIfPresent([DataGap].self, forKey: .dataGaps)) ?? []
        exampleLimit = water?.exampleLimit?.value
    }
}

/// GeoJSON Polygon or MultiPolygon; only the outer rings are kept.
struct Geometry: Decodable, Sendable {
    let rings: [[CLLocationCoordinate2D]]

    private enum CodingKeys: String, CodingKey { case type, coordinates }

    init(rings: [[CLLocationCoordinate2D]]) { self.rings = rings }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let type = try c.decode(String.self, forKey: .type)
        func ring(_ pts: [[Double]]) -> [CLLocationCoordinate2D] {
            pts.compactMap { $0.count >= 2 ? CLLocationCoordinate2D(latitude: $0[1], longitude: $0[0]) : nil }
        }
        switch type {
        case "Polygon":
            let coords = try c.decode([[[Double]]].self, forKey: .coordinates)
            rings = coords.prefix(1).map(ring)
        case "MultiPolygon":
            let coords = try c.decode([[[[Double]]]].self, forKey: .coordinates)
            rings = coords.compactMap { $0.first }.map(ring)
        default:
            rings = []
        }
    }

    /// Bounding box as (minLat, minLon, maxLat, maxLon).
    var bounds: (minLat: Double, minLon: Double, maxLat: Double, maxLon: Double)? {
        let all = rings.flatMap { $0 }
        guard let first = all.first else { return nil }
        var b = (minLat: first.latitude, minLon: first.longitude, maxLat: first.latitude, maxLon: first.longitude)
        for p in all {
            b.minLat = min(b.minLat, p.latitude); b.maxLat = max(b.maxLat, p.latitude)
            b.minLon = min(b.minLon, p.longitude); b.maxLon = max(b.maxLon, p.longitude)
        }
        return b
    }
}

/// One entry of `nasa_datasets`: the "NASA data behind this field" list.
struct NasaDataset: Decodable, Sendable, Identifiable {
    let id: String
    let name: String
    let tellsYou: String?
    let resolution: String?
    let status: String?
    let sourceURL: String?
    let note: String?

    enum CodingKeys: String, CodingKey {
        case id, name, resolution, status, note
        case tellsYou = "tells_you"
        case sourceURL = "source_url"
    }
}

/// Sand, silt and clay percentages (top metre or 3 feet).
struct SoilMix: Sendable, Equatable {
    let sand: Double, silt: Double, clay: Double
    private var total: Double { max(sand + silt + clay, 1) }
    var sandShare: Double { sand / total }
    var siltShare: Double { silt / total }
}

struct LocationList: Decodable, Sendable {
    let items: [FieldLocation]
}
