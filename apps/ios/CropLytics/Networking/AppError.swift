import Foundation

/// Errors the app shows to people, in plain words.
enum AppError: Error, Equatable, Sendable {
    /// No internet connection.
    case offline
    /// The free server did not wake up within the wait.
    case serverAsleep
    /// The route is not on the server (yet).
    case notFound
    case http(Int)
    case decoding(String)
    case other(String)

    init(_ error: Error) {
        if let e = error as? AppError { self = e; return }
        if let u = error as? URLError {
            switch u.code {
            case .notConnectedToInternet, .dataNotAllowed, .internationalRoamingOff: self = .offline
            case .timedOut, .cannotConnectToHost, .networkConnectionLost: self = .serverAsleep
            default: self = .other(u.localizedDescription)
            }
            return
        }
        if error is DecodingError { self = .decoding(String(describing: error)); return }
        self = .other(error.localizedDescription)
    }

    var title: String {
        switch self {
        case .offline: "You're offline"
        case .serverAsleep: "The server didn't wake up"
        case .notFound: "Not on the server yet"
        case .http: "The server had a problem"
        case .decoding: "Couldn't read the server's answer"
        case .other: "Something went wrong"
        }
    }

    var message: String {
        switch self {
        case .offline: "Connect to the internet and try again. Fields you opened before still show what you saw last time."
        case .serverAsleep: "The free server can take up to a minute to start. Try again in a moment."
        case .notFound: "This part of the data hasn't been published for this field yet."
        case .http(let code): "The server answered with error \(code). Try again in a moment."
        case .decoding: "The data changed shape. Update the app, or try again later."
        case .other(let text): text
        }
    }
}
