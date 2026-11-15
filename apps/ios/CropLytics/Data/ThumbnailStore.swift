import MapKit
import UIKit
import Observation

/// Satellite thumbnails of each field with its outline, drawn by MapKit and saved to disk,
/// so the field list shows pictures offline after the first visit.
@MainActor
@Observable
final class ThumbnailStore {
    private(set) var images: [String: UIImage] = [:]
    private var pending: Set<String> = []
    private let directory: URL?
    private let enabled: Bool

    init(directory: URL? = ThumbnailStore.defaultDirectory(), enabled: Bool = true) {
        self.directory = directory
        self.enabled = enabled
    }

    static func defaultDirectory() -> URL {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0].appending(path: "FieldThumbnails", directoryHint: .isDirectory)
    }

    func image(for id: String) -> UIImage? { images[id] }

    /// Loads from disk or draws a new snapshot. Safe to call repeatedly.
    func load(_ field: FieldLocation, size: CGSize = CGSize(width: 96, height: 72)) async {
        let id = field.id
        guard images[id] == nil, !pending.contains(id) else { return }
        if let file = fileURL(id), let data = try? Data(contentsOf: file), let img = UIImage(data: data) {
            images[id] = img
            return
        }
        guard enabled else { return }
        pending.insert(id)
        defer { pending.remove(id) }
        guard let image = await Self.snapshot(field, size: size) else { return }
        images[id] = image
        if let file = fileURL(id), let png = image.pngData() {
            try? FileManager.default.createDirectory(at: file.deletingLastPathComponent(), withIntermediateDirectories: true)
            try? png.write(to: file, options: .atomic)
        }
    }

    private func fileURL(_ id: String) -> URL? { directory?.appending(path: "\(id)-v1.png") }

    /// MapKit satellite imagery with the field outline in the selection yellow and a dark shadow.
    static func snapshot(_ field: FieldLocation, size: CGSize) async -> UIImage? {
        let region = FieldMapRegion.region(for: field, padding: 1.5)
        let options = MKMapSnapshotter.Options()
        options.region = region
        options.size = size
        options.scale = 3
        options.preferredConfiguration = MKImageryMapConfiguration()
        let snapshotter = MKMapSnapshotter(options: options)
        let rings = field.geometry?.rings ?? []
        return await withCheckedContinuation { continuation in
            snapshotter.start(with: .main) { shot, _ in
                continuation.resume(returning: shot.map { draw($0, rings: rings, size: size) })
            }
        }
    }

    private nonisolated static func draw(_ shot: MKMapSnapshotter.Snapshot, rings: [[CLLocationCoordinate2D]], size: CGSize) -> UIImage {
        let renderer = UIGraphicsImageRenderer(size: size)
        return renderer.image { ctx in
            shot.image.draw(at: .zero)
            let cg = ctx.cgContext
            cg.setLineJoin(.round)
            for ring in rings where ring.count > 2 {
                let points = ring.map { shot.point(for: $0) }
                cg.beginPath()
                cg.addLines(between: points)
                cg.closePath()
                cg.setShadow(offset: CGSize(width: 0, height: 1), blur: 2, color: UIColor.black.withAlphaComponent(0.8).cgColor)
                cg.setStrokeColor(UIColor(hex: 0xFFD166).cgColor)
                cg.setLineWidth(1.5)
                cg.strokePath()
            }
        }
    }
}

enum FieldMapRegion {
    /// A region around the field outline; `padding` 1.0 = the outline's own extent.
    static func region(for field: FieldLocation, padding: Double) -> MKCoordinateRegion {
        if let b = field.geometry?.bounds {
            let center = CLLocationCoordinate2D(latitude: (b.minLat + b.maxLat) / 2, longitude: (b.minLon + b.maxLon) / 2)
            let span = MKCoordinateSpan(latitudeDelta: max(b.maxLat - b.minLat, 0.004) * padding,
                                        longitudeDelta: max(b.maxLon - b.minLon, 0.004) * padding)
            return MKCoordinateRegion(center: center, span: span)
        }
        return MKCoordinateRegion(center: field.centroid.clCoordinate, span: MKCoordinateSpan(latitudeDelta: 0.012, longitudeDelta: 0.012))
    }
}
