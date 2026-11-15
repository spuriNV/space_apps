import Foundation

/// The app's single source of field data. Screens never talk to the API directly.
protocol FieldRepository: Sendable {
    /// Offline-first: yields the saved copy (if any) at once, then the live answer.
    func stream<T: Decodable & Sendable>(_ endpoint: Endpoint, as type: T.Type) -> AsyncThrowingStream<Fetched<T>, Error>
    /// Re-scores the rotations for a water limit (POST .../score). Falls back to the last saved score for that limit.
    func score(fieldID: String, allocation: Double) async throws -> Fetched<[Strategy]>
}

extension FieldRepository {
    func locations() -> AsyncThrowingStream<Fetched<[FieldLocation]>, Error> { mapped(.locations, LocationList.self) { $0.items } }
    func nasaNow(_ id: String) -> AsyncThrowingStream<Fetched<NasaNow>, Error> { stream(.nasaNow(id), as: NasaNow.self) }
    func calendar(_ id: String) -> AsyncThrowingStream<Fetched<FieldCalendar>, Error> { stream(.calendar(id), as: FieldCalendar.self) }
    func strategies(_ id: String) -> AsyncThrowingStream<Fetched<[Strategy]>, Error> { mapped(.strategies(id), StrategyList.self) { $0.items } }
    func outlook(_ id: String) -> AsyncThrowingStream<Fetched<Outlook>, Error> { stream(.outlook(id), as: Outlook.self) }
    func models(_ id: String) -> AsyncThrowingStream<Fetched<ModelReport>, Error> { stream(.models(id), as: ModelReport.self) }
    func stress(_ id: String) -> AsyncThrowingStream<Fetched<StressReport>, Error> { stream(.stress(id), as: StressReport.self) }
    func waterSeen(_ id: String) -> AsyncThrowingStream<Fetched<WaterSeen>, Error> { stream(.waterSeen(id), as: WaterSeen.self) }
    func insurance(_ id: String) -> AsyncThrowingStream<Fetched<InsuranceProfile>, Error> { stream(.insurance(id), as: InsuranceProfile.self) }
    func glossary() -> AsyncThrowingStream<Fetched<Glossary>, Error> { stream(.glossary, as: Glossary.self) }

    private func mapped<Raw: Decodable & Sendable, Out: Sendable>(
        _ endpoint: Endpoint, _ raw: Raw.Type, _ transform: @escaping @Sendable (Raw) -> Out
    ) -> AsyncThrowingStream<Fetched<Out>, Error> {
        let upstream = stream(endpoint, as: raw)
        return AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    for try await item in upstream {
                        continuation.yield(Fetched(value: transform(item.value), savedAt: item.savedAt))
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }
}

/// Live repository: memory (a few minutes) -> saved copy on disk -> network, with in-flight requests shared.
final class LiveFieldRepository: FieldRepository {
    private let api: APIClient
    private let cache: ResponseCache
    private let memory = MemoryStore()
    private let memoryLifetime: TimeInterval

    init(api: APIClient, cache: ResponseCache, memoryLifetime: TimeInterval = 600) {
        self.api = api
        self.cache = cache
        self.memoryLifetime = memoryLifetime
    }

    func stream<T: Decodable & Sendable>(_ endpoint: Endpoint, as type: T.Type) -> AsyncThrowingStream<Fetched<T>, Error> {
        let api = self.api, cache = self.cache, memory = self.memory, lifetime = memoryLifetime
        return AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    if let hot = await memory.recent(endpoint.cacheKey, within: lifetime),
                       let value = try? APIClient.decode(T.self, from: hot) {
                        continuation.yield(Fetched(value: value, savedAt: nil))
                        continuation.finish()
                        return
                    }
                    if let saved = await cache.read(endpoint.cacheKey),
                       let value = try? APIClient.decode(T.self, from: saved.body) {
                        continuation.yield(Fetched(value: value, savedAt: saved.savedAt))
                    }
                    let data = try await memory.shared(endpoint.cacheKey) { try await api.data(for: endpoint) }
                    let value = try APIClient.decode(T.self, from: data)
                    await cache.write(data, for: endpoint.cacheKey)
                    continuation.yield(Fetched(value: value, savedAt: nil))
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    func score(fieldID: String, allocation: Double) async throws -> Fetched<[Strategy]> {
        let endpoint = Endpoint.score(fieldID, allocation: allocation)
        do {
            let data = try await api.data(for: endpoint)
            let list = try APIClient.decode(StrategyList.self, from: data)
            await cache.write(data, for: endpoint.cacheKey)
            return Fetched(value: list.items, savedAt: nil)
        } catch {
            if let saved = await cache.read(endpoint.cacheKey),
               let list = try? APIClient.decode(StrategyList.self, from: saved.body) {
                return Fetched(value: list.items, savedAt: saved.savedAt)
            }
            throw AppError(error)
        }
    }
}

/// Recent responses in memory, and one shared network call per route at a time.
actor MemoryStore {
    private var recentData: [String: (data: Data, at: Date)] = [:]
    private var inFlight: [String: Task<Data, Error>] = [:]

    func recent(_ key: String, within seconds: TimeInterval) -> Data? {
        guard let hit = recentData[key], Date.now.timeIntervalSince(hit.at) < seconds else { return nil }
        return hit.data
    }

    func shared(_ key: String, _ work: @escaping @Sendable () async throws -> Data) async throws -> Data {
        if let running = inFlight[key] { return try await running.value }
        let task = Task { try await work() }
        inFlight[key] = task
        defer { inFlight[key] = nil }
        let data = try await task.value
        recentData[key] = (data, .now)
        return data
    }
}
