import Foundation
import Observation
import SwiftUI

/// Everything a screen depends on, injected through the SwiftUI environment.
/// The live app, the UI tests and the previews each build their own.
@MainActor
@Observable
final class AppEnvironment {
    let repository: any FieldRepository
    let limits: WaterLimitStore
    let thumbnails: ThumbnailStore
    let serverStatus: ServerStatus
    /// "Today" for the screens; fixed in tests and previews so the answers don't drift.
    let today: @Sendable () -> Date

    init(repository: any FieldRepository, limits: WaterLimitStore, thumbnails: ThumbnailStore, serverStatus: ServerStatus,
         today: @escaping @Sendable () -> Date = { Date.now }) {
        self.repository = repository
        self.limits = limits
        self.thumbnails = thumbnails
        self.serverStatus = serverStatus
        self.today = today
    }

    /// The real app: live API on Render, saved copies in Application Support.
    static func live() -> AppEnvironment {
        let status = ServerStatus()
        let config = URLSessionConfiguration.default
        config.waitsForConnectivity = false
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        let api = APIClient(config: .live, session: URLSession(configuration: config), onEvent: status.sink())
        let repo = LiveFieldRepository(api: api, cache: ResponseCache(directory: ResponseCache.defaultDirectory()))
        return AppEnvironment(repository: repo, limits: WaterLimitStore(), thumbnails: ThumbnailStore(), serverStatus: status)
    }

    /// Bundled example payloads served through a URLProtocol: deterministic UI tests and previews, no network.
    /// `wakeDelay` simulates the sleeping free server.
    static func fixtures(wakeDelay: Duration = .zero, freshStorage: Bool = true) -> AppEnvironment {
        let status = ServerStatus()
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [FixtureURLProtocol.self]
        FixtureURLProtocol.delay = wakeDelay
        var apiConfig = APIConfig.live
        apiConfig.wakeNoticeAfter = .milliseconds(500)
        let api = APIClient(config: apiConfig, session: URLSession(configuration: config), onEvent: status.sink())
        let dir = FileManager.default.temporaryDirectory.appending(path: "CropLyticsFixtureCache-\(UUID().uuidString)")
        let repo = LiveFieldRepository(api: api, cache: ResponseCache(directory: dir))
        let defaults = UserDefaults(suiteName: "CropLyticsFixtures")!
        if freshStorage { defaults.removePersistentDomain(forName: "CropLyticsFixtures") }
        return AppEnvironment(repository: repo, limits: WaterLimitStore(defaults: defaults),
                              thumbnails: ThumbnailStore(directory: nil, enabled: false), serverStatus: status,
                              today: { FixtureURLProtocol.fixtureToday })
    }
}

/// Serves Resources/Fixtures/*.json for API paths: `locations` -> locations.json, `locations/{id}/{route}` -> {id}__{route}.json.
/// Routes without a fixture answer 404, as the live server does for routes it doesn't have yet.
final class FixtureURLProtocol: URLProtocol, @unchecked Sendable {
    nonisolated(unsafe) static var delay: Duration = .zero
    static let fixtureToday: Date = GrowerDate.parse("2026-11-14")!

    static func fixtureData(for url: URL, bundle: Bundle = .main) -> Data? {
        let parts = url.path.split(separator: "/").map(String.init).drop { $0 != "api" }.dropFirst()
        let name: String
        switch parts.count {
        case 1: name = parts[parts.startIndex]
        case 3 where parts.first == "locations": name = "\(parts[parts.startIndex + 1])__\(parts[parts.startIndex + 2])"
        default: return nil
        }
        guard let file = bundle.url(forResource: name, withExtension: "json", subdirectory: "Fixtures") else { return nil }
        return try? Data(contentsOf: file)
    }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        let request = self.request
        let delay = Self.delay
        Task { [weak self] in
            if delay > .zero { try? await Task.sleep(for: delay) }
            guard let self, let url = request.url else { return }
            let data = Self.fixtureData(for: url)
            let status = data == nil ? 404 : 200
            let body = data ?? Data(#"{"detail":"not found"}"#.utf8)
            let response = HTTPURLResponse(url: url, statusCode: status, httpVersion: "HTTP/1.1", headerFields: ["Content-Type": "application/json"])!
            self.client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            self.client?.urlProtocol(self, didLoad: body)
            self.client?.urlProtocolDidFinishLoading(self)
        }
    }

    override func stopLoading() {}
}
