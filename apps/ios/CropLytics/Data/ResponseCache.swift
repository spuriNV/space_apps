import Foundation

/// Offline-first file cache: the last answer for each route, with the date it was saved.
/// Lives in Application Support (not Caches, which iOS may purge) and is excluded from iCloud backup.
actor ResponseCache {
    struct Entry: Codable, Sendable {
        let savedAt: Date
        let body: Data
    }

    private let directory: URL
    private let fileManager = FileManager.default

    init(directory: URL) {
        self.directory = directory
    }

    static func defaultDirectory() -> URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appending(path: "ResponseCache", directoryHint: .isDirectory)
    }

    func read(_ key: String) -> Entry? {
        guard let data = try? Data(contentsOf: fileURL(key)) else { return nil }
        return try? PropertyListDecoder().decode(Entry.self, from: data)
    }

    func write(_ body: Data, for key: String, at date: Date = .now) {
        do {
            try ensureDirectory()
            let encoder = PropertyListEncoder()
            encoder.outputFormat = .binary
            let data = try encoder.encode(Entry(savedAt: date, body: body))
            try data.write(to: fileURL(key), options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
        } catch {
            // A cache write failing must never break the screen; the next load simply fetches again.
        }
    }

    func clear() {
        try? fileManager.removeItem(at: directory)
    }

    private func ensureDirectory() throws {
        guard !fileManager.fileExists(atPath: directory.path(percentEncoded: false)) else { return }
        try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
        var url = directory
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try? url.setResourceValues(values)
    }

    private func fileURL(_ key: String) -> URL {
        let safe = key.map { $0.isLetter || $0.isNumber || $0 == "." || $0 == "-" ? $0 : "_" }
        return directory.appending(path: String(safe) + ".plist")
    }
}
