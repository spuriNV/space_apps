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

        enum CodingKeys: String, CodingKey {
            case muname
            case drainageClass = "drainage_class"
            case hydrologicGroup = "hydrologic_group"
            case textureClass = "texture_class"
            case ecDsPerM = "ec_ds_per_m"
            case awcMmPerM = "awc_mm_per_m"
            case omPct = "om_pct"
        }

        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            muname = try? c.decodeIfPresent(String.self, forKey: .muname)
            drainageClass = try? c.decodeIfPresent(String.self, forKey: .drainageClass)
            hydrologicGroup = try? c.decodeIfPresent(String.self, forKey: .hydrologicGroup)
            textureClass = try? c.decodeIfPresent(String.self, forKey: .textureClass)
            ecDsPerM = (try? c.decodeIfPresent(LossyDouble.self, forKey: .ecDsPerM))?.value
            awcMmPerM = try? c.decodeIfPresent(SourcedNumber.self, forKey: .awcMmPerM)
            omPct = try? c.decodeIfPresent(SourcedNumber.self, forKey: .omPct)
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
        enum CodingKeys: String, CodingKey {
            case source, district
            case sgmaSubbasin = "sgma_subbasin"
        }
        var isSurface: Bool { source == "surface" }
    }

    struct FieldEvent: Decodable, Sendable, Identifiable {
        let date: String
        let title: String
        let url: String?
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

struct LocationList: Decodable, Sendable {
    let items: [FieldLocation]
}
