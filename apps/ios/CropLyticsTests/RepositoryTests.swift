import Foundation
import Testing
@testable import CropLytics

@Suite("Offline-first repository")
@MainActor
struct RepositoryTests {
    @Test("Shows the saved copy with its date when the server can't be reached")
    func savedCopyWhenOffline() async throws {
        let dir = TestAPI.tempDir()
        // First visit: online, the answer is saved.
        let online = TestAPI.fixtureRepository(cacheDir: dir)
        var first: LoadState<NasaNow> = .idle
        await consume(online.nasaNow("car_colusa_rice")) { first = $0 }
        #expect(first.freshness == .live)

        // Later: offline, a fresh repository (empty memory) reads the saved copy.
        let (api, _) = TestAPI.client { _ in throw URLError(.notConnectedToInternet) }
        let offline = LiveFieldRepository(api: api, cache: ResponseCache(directory: dir))
        var states: [LoadState<NasaNow>] = []
        await consume(offline.nasaNow("car_colusa_rice")) { states.append($0) }
        let last = try #require(states.last)
        #expect(last.value?.reading("imerg_wy_to_date_mm")?.value == 48)
        #expect(last.freshness?.savedAt != nil)
        #expect(last.freshness?.refreshError == .offline)
    }

    @Test("Without a saved copy, offline is an error state")
    func errorWithoutCache() async {
        let (api, _) = TestAPI.client { _ in throw URLError(.notConnectedToInternet) }
        let repo = LiveFieldRepository(api: api, cache: ResponseCache(directory: TestAPI.tempDir()))
        var state: LoadState<[FieldLocation]> = .idle
        await consume(repo.locations()) { state = $0 }
        #expect(state.error == .offline)
    }

    @Test("Re-scoring falls back to the last saved score for that limit")
    func scoreFallsBack() async throws {
        let dir = TestAPI.tempDir()
        _ = try await TestAPI.fixtureRepository(cacheDir: dir).score(fieldID: "car_colusa_rice", allocation: 3.0)
        let (api, _) = TestAPI.client { _ in (503, Data()) }
        let repo = LiveFieldRepository(api: api, cache: ResponseCache(directory: dir))
        let saved = try await repo.score(fieldID: "car_colusa_rice", allocation: 3.0)
        #expect(saved.savedAt != nil)
        #expect(saved.value.count == 4)
    }
}
