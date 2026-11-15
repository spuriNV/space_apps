import Foundation

/// One API route. `cacheKey` names the saved copy used for offline-first loading.
struct Endpoint: Sendable, Equatable {
    var method: String = "GET"
    var path: String
    var query: [URLQueryItem] = []
    var body: Data?
    var cacheKey: String

    init(method: String = "GET", path: String, query: [URLQueryItem] = [], body: Data? = nil, cacheKey: String? = nil) {
        self.method = method
        self.path = path
        self.query = query
        self.body = body
        let q = query.map { "\($0.name)=\($0.value ?? "")" }.joined(separator: "&")
        self.cacheKey = cacheKey ?? (path + (q.isEmpty ? "" : "?" + q))
    }
}

/// Every route the app uses (backend/api/README.md).
extension Endpoint {
    static let locations = Endpoint(path: "locations")
    static let glossary = Endpoint(path: "glossary")

    static func location(_ id: String) -> Endpoint { Endpoint(path: "locations/\(id)") }
    static func nasaNow(_ id: String) -> Endpoint { Endpoint(path: "locations/\(id)/nasa_now") }
    /// The NASA-native calendar (HLS) first; the app falls back to the Sentinel-2/Landsat calendar.
    static func calendar(_ id: String, hls: Bool = true) -> Endpoint {
        Endpoint(path: "locations/\(id)/calendar", query: hls ? [URLQueryItem(name: "source", value: "hls")] : [])
    }
    static func strategies(_ id: String) -> Endpoint { Endpoint(path: "locations/\(id)/strategies") }
    static func outlook(_ id: String) -> Endpoint { Endpoint(path: "locations/\(id)/outlook") }
    static func models(_ id: String) -> Endpoint { Endpoint(path: "locations/\(id)/models") }
    static func stress(_ id: String) -> Endpoint { Endpoint(path: "locations/\(id)/stress") }
    static func waterSeen(_ id: String) -> Endpoint { Endpoint(path: "locations/\(id)/water_seen") }
    static func insurance(_ id: String) -> Endpoint { Endpoint(path: "locations/\(id)/insurance") }

    /// POST .../score with the grower's water limit (acre-ft/acre). Saved per limit so it works offline too.
    static func score(_ id: String, allocation: Double) -> Endpoint {
        let body = try? JSONEncoder().encode(ScoreRequest(allocation: allocation))
        return Endpoint(method: "POST", path: "locations/\(id)/score", body: body,
                        cacheKey: "locations/\(id)/score?allocation=\(String(format: "%.1f", allocation))")
    }
}
