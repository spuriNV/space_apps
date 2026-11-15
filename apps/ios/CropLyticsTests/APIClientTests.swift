import Foundation
import Testing
@testable import CropLytics

@Suite("API client")
struct APIClientTests {
    @Test("Decodes the field list from the live payload shape")
    func decodesLocations() async throws {
        let (api, _) = TestAPI.client(handler: TestAPI.fixtures)
        let list = try await api.send(.locations, as: LocationList.self)
        #expect(list.items.map(\.id) == ["car_colusa_rice", "caf_tulare_forage"])
        let colusa = try #require(list.items.first)
        #expect(colusa.geometry?.rings.first?.count ?? 0 > 10)
        #expect(colusa.cropHistory["2025"] == "Rice")
        #expect(colusa.nasaDatasets.contains { $0.id == "imerg" && $0.status == "live" })
    }

    @Test("Builds GET URLs with the query, under /api/")
    func buildsRequests() {
        let api = APIClient(config: .live)
        let req = api.request(for: .calendar("car_colusa_rice"))
        #expect(req.url?.absoluteString == "https://croplytics-app.onrender.com/api/locations/car_colusa_rice/calendar?source=hls")
        #expect(req.httpMethod == "GET")
    }

    @Test("POST score sends the water limit as JSON")
    func scoreSendsAllocation() async throws {
        let (api, _) = TestAPI.client { req in
            #expect(req.httpMethod == "POST")
            #expect(req.url?.path().hasSuffix("/locations/car_colusa_rice/score") == true)
            let body = try JSONSerialization.jsonObject(with: req.httpBody ?? Data()) as? [String: Double]
            #expect(body?["allocation"] == 3.5)
            return try TestAPI.fixtures(req)
        }
        let result = try await api.send(.score("car_colusa_rice", allocation: 3.5), as: StrategyList.self)
        #expect(result.items.count == 4)
    }

    @Test("Waits while the free server wakes: retries 503 and reports a slow request")
    func retriesWhileWaking() async throws {
        let attempts = Counter()
        let log = EventLog()
        let (api, host) = TestAPI.client(maxWait: .seconds(5), onEvent: { log.append($0) }) { req in
            if attempts.next() < 3 {
                Thread.sleep(forTimeInterval: 0.02)
                return (503, Data("waking".utf8))
            }
            return try TestAPI.fixtures(req)
        }
        let list = try await api.send(.locations, as: LocationList.self)
        #expect(list.items.count == 2)
        #expect(StubURLProtocol.requestCount(host) == 4)
        #expect(log.slowCount == 1)
        #expect(log.finishedCount == 1)
    }

    @Test("Gives up with 'server asleep' after the wake wait")
    func givesUpAfterWait() async {
        let (api, _) = TestAPI.client(maxWait: .milliseconds(80)) { _ in (502, Data()) }
        await #expect(throws: AppError.serverAsleep) { try await api.data(for: .locations) }
    }

    @Test("404 means not on the server yet, with no retries")
    func notFoundIsNotRetried() async {
        let (api, host) = TestAPI.client { _ in (404, Data()) }
        await #expect(throws: AppError.notFound) { try await api.data(for: .stress("car_colusa_rice")) }
        #expect(StubURLProtocol.requestCount(host) == 1)
    }

    @Test("No connection maps to offline")
    func offline() async {
        let (api, _) = TestAPI.client { _ in throw URLError(.notConnectedToInternet) }
        await #expect(throws: AppError.offline) { try await api.data(for: .locations) }
    }

    @Test("A changed payload shape is a decoding error, not a crash")
    func decodingError() async {
        let (api, _) = TestAPI.client { _ in (200, Data(#"{"items": 3}"#.utf8)) }
        await #expect {
            try await api.send(.locations, as: LocationList.self)
        } throws: { error in
            if case AppError.decoding = error { return true }
            return false
        }
    }
}

final class Counter: @unchecked Sendable {
    private let lock = NSLock()
    private var n = 0
    func next() -> Int { lock.withLock { defer { n += 1 }; return n } }
}
