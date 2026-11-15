import Foundation

/// Settings for the API client. The defaults suit the live server on Render's free plan,
/// which sleeps when idle and takes up to about 50 seconds to answer the first request.
struct APIConfig: Sendable {
    var baseURL: URL
    /// After this long without an answer, the app says "Waking the server, up to a minute".
    var wakeNoticeAfter: Duration = .seconds(3)
    /// Keep retrying 502/503/504 and timeouts for this long before giving up.
    var maxWakeWait: Duration = .seconds(90)
    /// First retry delay; doubles each time up to `maxRetryDelay`.
    var retryDelay: Duration = .seconds(2)
    var maxRetryDelay: Duration = .seconds(8)
    /// Per-request timeout (a waking server can hold a request open for ~50 s).
    var requestTimeout: TimeInterval = 75

    static let live = APIConfig(baseURL: URL(string: "https://croplytics-app.onrender.com/api/")!)
}

/// What the client tells the UI while a request is slow.
enum NetworkEvent: Sendable {
    case slow(UUID)
    case finished(UUID)
}

/// A small typed client on URLSession: builds requests, retries while the free server wakes, decodes JSON.
final class APIClient: Sendable {
    let config: APIConfig
    private let session: URLSession
    private let onEvent: @Sendable (NetworkEvent) -> Void

    init(config: APIConfig = .live, session: URLSession = .shared, onEvent: @escaping @Sendable (NetworkEvent) -> Void = { _ in }) {
        self.config = config
        self.session = session
        self.onEvent = onEvent
    }

    func request(for endpoint: Endpoint) -> URLRequest {
        var url = endpoint.path.hasPrefix("/")
            ? (URL(string: endpoint.path, relativeTo: config.baseURL)?.absoluteURL ?? config.baseURL)
            : config.baseURL.appending(path: endpoint.path)
        if !endpoint.query.isEmpty { url.append(queryItems: endpoint.query) }
        var req = URLRequest(url: url, timeoutInterval: config.requestTimeout)
        req.httpMethod = endpoint.method
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body = endpoint.body {
            req.httpBody = body
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        return req
    }

    /// Raw response body. Retries while the server wakes; throws `AppError`.
    func data(for endpoint: Endpoint) async throws -> Data {
        let id = UUID()
        let clock = ContinuousClock()
        let start = clock.now
        let notice = config.wakeNoticeAfter
        let onEvent = self.onEvent
        let watchdog = Task {
            try await Task.sleep(for: notice)
            onEvent(.slow(id))
        }
        defer {
            watchdog.cancel()
            onEvent(.finished(id))
        }

        var delay = config.retryDelay
        let req = request(for: endpoint)
        while true {
            try Task.checkCancellation()
            do {
                let (data, response) = try await session.data(for: req)
                let status = (response as? HTTPURLResponse)?.statusCode ?? 0
                switch status {
                case 200..<300:
                    return data
                case 404:
                    throw AppError.notFound
                case 429, 502, 503, 504:
                    // Render answers 502/503 while the free instance spins up.
                    guard clock.now - start + delay < config.maxWakeWait else { throw AppError.serverAsleep }
                default:
                    throw AppError.http(status)
                }
            } catch let error as URLError where Self.isWakeRetryable(error) {
                guard clock.now - start + delay < config.maxWakeWait else { throw AppError(error) }
            } catch let error as AppError {
                throw error
            } catch is CancellationError {
                throw CancellationError()
            } catch {
                throw AppError(error)
            }
            try await Task.sleep(for: delay)
            delay = min(delay * 2, config.maxRetryDelay)
        }
    }

    /// Decoded response.
    func send<T: Decodable & Sendable>(_ endpoint: Endpoint, as type: T.Type = T.self) async throws -> T {
        let data = try await data(for: endpoint)
        return try Self.decode(type, from: data)
    }

    static func decode<T: Decodable>(_ type: T.Type, from data: Data) throws -> T {
        do {
            return try JSONDecoder().decode(type, from: data)
        } catch {
            throw AppError.decoding(String(describing: error))
        }
    }

    private static func isWakeRetryable(_ error: URLError) -> Bool {
        [.timedOut, .cannotConnectToHost, .networkConnectionLost, .cannotFindHost, .badServerResponse].contains(error.code)
    }
}
