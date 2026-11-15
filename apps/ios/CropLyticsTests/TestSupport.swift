import Foundation
@testable import CropLytics

/// URLProtocol stub. Each test gets its own fake host, so suites can run side by side without sharing handlers.
final class StubURLProtocol: URLProtocol, @unchecked Sendable {
    typealias Handler = @Sendable (URLRequest) throws -> (Int, Data)
    private static let lock = NSLock()
    nonisolated(unsafe) private static var handlers: [String: Handler] = [:]
    nonisolated(unsafe) private static var counts: [String: Int] = [:]

    static func register(_ handler: @escaping Handler) -> String {
        let host = "stub-\(UUID().uuidString.lowercased()).test"
        lock.withLock { handlers[host] = handler; counts[host] = 0 }
        return host
    }

    static func requestCount(_ host: String) -> Int { lock.withLock { counts[host] ?? 0 } }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        let host = request.url?.host() ?? ""
        let handler = Self.lock.withLock { () -> Handler? in
            Self.counts[host, default: 0] += 1
            return Self.handlers[host]
        }
        guard let handler else {
            client?.urlProtocol(self, didFailWithError: URLError(.unsupportedURL))
            return
        }
        do {
            var req = request
            if req.httpBody == nil, let stream = req.httpBodyStream { req.httpBody = Data(reading: stream) }
            let (status, data) = try handler(req)
            let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: "HTTP/1.1", headerFields: nil)!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}

extension Data {
    init(reading stream: InputStream) {
        self.init()
        stream.open()
        defer { stream.close() }
        let size = 4096
        var buffer = [UInt8](repeating: 0, count: size)
        while stream.hasBytesAvailable {
            let n = stream.read(&buffer, maxLength: size)
            if n <= 0 { break }
            append(buffer, count: n)
        }
    }
}

enum TestAPI {
    /// A client whose requests go to `handler`. Short waits so retry tests run fast.
    static func client(maxWait: Duration = .milliseconds(400), onEvent: @escaping @Sendable (NetworkEvent) -> Void = { _ in },
                       handler: @escaping StubURLProtocol.Handler) -> (APIClient, String) {
        let host = register(handler)
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [StubURLProtocol.self]
        var api = APIConfig(baseURL: URL(string: "https://\(host)/api/")!)
        api.wakeNoticeAfter = .milliseconds(30)
        api.maxWakeWait = maxWait
        api.retryDelay = .milliseconds(10)
        api.maxRetryDelay = .milliseconds(20)
        return (APIClient(config: api, session: URLSession(configuration: config), onEvent: onEvent), host)
    }

    static func register(_ handler: @escaping StubURLProtocol.Handler) -> String { StubURLProtocol.register(handler) }

    /// Serves the app's bundled fixtures, like the live API.
    static let fixtures: StubURLProtocol.Handler = { req in
        guard let url = req.url, let data = FixtureURLProtocol.fixtureData(for: url, bundle: Bundle(for: FixtureURLProtocol.self)) else {
            return (404, Data(#"{"detail":"not found"}"#.utf8))
        }
        return (200, data)
    }

    static func fixtureRepository(cacheDir: URL = tempDir()) -> LiveFieldRepository {
        let (api, _) = client(handler: fixtures)
        return LiveFieldRepository(api: api, cache: ResponseCache(directory: cacheDir))
    }

    static func tempDir() -> URL {
        FileManager.default.temporaryDirectory.appending(path: "CropLyticsTests-\(UUID().uuidString)")
    }

    static func fixture<T: Decodable>(_ name: String, as: T.Type) throws -> T {
        let url = Bundle(for: FixtureURLProtocol.self).url(forResource: name, withExtension: "json", subdirectory: "Fixtures")!
        return try JSONDecoder().decode(T.self, from: Data(contentsOf: url))
    }

    @MainActor static func limits() -> WaterLimitStore {
        let suite = "CropLyticsTests-\(UUID().uuidString)"
        return WaterLimitStore(defaults: UserDefaults(suiteName: suite)!)
    }

    static let today = GrowerDate.parse("2026-11-14")!
    static let todayPoint = TimePoint(iso: "2026-11-14")!
}

/// Thread-safe counter for events reported by the client.
final class EventLog: @unchecked Sendable {
    private let lock = NSLock()
    private var events: [NetworkEvent] = []
    func append(_ e: NetworkEvent) { lock.withLock { events.append(e) } }
    var slowCount: Int { lock.withLock { events.filter { if case .slow = $0 { true } else { false } }.count } }
    var finishedCount: Int { lock.withLock { events.filter { if case .finished = $0 { true } else { false } }.count } }
}
