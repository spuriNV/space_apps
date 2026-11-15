import SwiftUI
import MapLibre

/// What the map draws, built by `FieldsMap` from the app state. Plain values so the representable can diff them.
struct MapContent: Equatable {
    struct Pin: Equatable { let id: String, name: String, lon: Double, lat: Double, selected: Bool }
    struct Outline: Equatable { let id: String, ring: [[Double]], selected: Bool, tint: String }
    struct Footprint: Equatable { let ring: [[Double]], color: String }
    var pins: [Pin] = []
    var outlines: [Outline] = []
    var footprints: [Footprint] = []
    var reserves: [[[Double]]] = []
    var cells: [Map3D.Extrusion] = [], smap: [Map3D.Extrusion] = [], grace: [Map3D.Extrusion] = [], posts: [Map3D.Extrusion] = []
    var shadow: [[[Double]]] = []
}

/// A camera command; `id` is bumped for each so the same command twice still flies.
struct MapCommand: Equatable {
    enum Kind: Equatable {
        case home
        case card(bounds: [Double]?, lat: Double, lon: Double)           // w, s, e, n
        case drill(lat: Double, lon: Double, small: Bool)
    }
    var id = 0
    var kind: Kind = .home
}

struct CameraState: Equatable { var zoom = 0.0, pitch = 0.0, heading = 0.0 }

/// MapLibre Native in SwiftUI. Everything that moves with zoom is a style expression; the camera is written only for
/// commands (flights) and once a pinch ends, never from inside the gesture, so a pinch is never cancelled.
struct MapLibreView: UIViewRepresentable {
    let content: MapContent
    let command: MapCommand
    let topInset: CGFloat
    let bottomInset: CGFloat
    let reduceMotion: Bool
    /// The open field's centre, for the tilt that follows a pinch.
    let focus: CLLocationCoordinate2D?
    let onSelect: (String) -> Void
    let onCamera: (CameraState) -> Void

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> MLNMapView {
        let map = MLNMapView(frame: .zero, styleURL: MapStyle.writeToDisk())
        map.delegate = context.coordinator
        map.automaticallyAdjustsContentInset = false
        map.attributionButton.isHidden = false
        map.compassView.isHidden = true
        map.maximumZoomLevel = 19
        map.setCenter(CLLocationCoordinate2D(latitude: Map3D.homeLat, longitude: Map3D.homeLon), zoomLevel: Map3D.homeZoom, animated: false)
        map.accessibilityLabel = "Satellite map of the fields"
        let tap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.tapped(_:)))
        for r in map.gestureRecognizers ?? [] { if let t = r as? UITapGestureRecognizer, t.numberOfTapsRequired == 2 { tap.require(toFail: t) } }
        map.addGestureRecognizer(tap)
        context.coordinator.map = map
        return map
    }

    func updateUIView(_ map: MLNMapView, context: Context) {
        let c = context.coordinator
        c.onSelect = onSelect; c.onCamera = onCamera; c.focus = focus; c.reduceMotion = reduceMotion
        let inset = UIEdgeInsets(top: topInset, left: 0, bottom: bottomInset, right: 0)
        if map.contentInset != inset { map.setContentInset(inset, animated: false, completionHandler: nil) }
        c.content = content
        c.applyContent()
        if command.id != c.lastCommand { c.lastCommand = command.id; c.run(command) }
    }

    @MainActor
    final class Coordinator: NSObject, @preconcurrency MLNMapViewDelegate {
        weak var map: MLNMapView?
        var onSelect: (String) -> Void = { _ in }
        var onCamera: (CameraState) -> Void = { _ in }
        var focus: CLLocationCoordinate2D?
        var reduceMotion = false
        var content = MapContent()
        var lastCommand = 0
        private var loaded = false
        private var applied = MapContent()
        private var pending: MapCommand?

        func mapView(_ mapView: MLNMapView, didFinishLoading style: MLNStyle) {
            loaded = true
            applied = MapContent()
            applyContent(force: true)
            if let p = pending { pending = nil; run(p) }
            report()
        }

        // MARK: sources

        private func set(_ id: String, _ features: [[String: Any]]) {
            guard let src = map?.style?.source(withIdentifier: id) as? MLNShapeSource else { return }
            let json: [String: Any] = ["type": "FeatureCollection", "features": features]
            guard let data = try? JSONSerialization.data(withJSONObject: json),
                  let shape = try? MLNShape(data: data, encoding: String.Encoding.utf8.rawValue) else { return }
            src.shape = shape
        }
        private static func poly(_ ring: [[Double]], _ props: [String: Any] = [:]) -> [String: Any] {
            ["type": "Feature", "properties": props, "geometry": ["type": "Polygon", "coordinates": [ring]]]
        }
        private static func ext(_ e: Map3D.Extrusion) -> [String: Any] { poly(e.ring, ["b": e.base, "h": e.height, "col": e.color]) }

        func applyContent(force: Bool = false) {
            guard loaded else { return }
            let a = applied, n = content
            if force || a.pins != n.pins {
                set("pins", n.pins.map { ["type": "Feature", "properties": ["id": $0.id, "name": $0.name, "selected": $0.selected],
                                          "geometry": ["type": "Point", "coordinates": [$0.lon, $0.lat]]] })
            }
            if force || a.outlines != n.outlines {
                set("field", n.outlines.map { Self.poly($0.ring, ["id": $0.id, "selected": $0.selected, "tint": $0.tint]) })
            }
            if force || a.footprints != n.footprints { set("fp", n.footprints.map { Self.poly($0.ring, ["color": $0.color]) }) }
            if force || a.reserves != n.reserves {
                set("reserves", n.reserves.map { ["type": "Feature", "properties": [:], "geometry": ["type": "LineString", "coordinates": $0]] })
            }
            if force || a.cells != n.cells { set("cells", n.cells.map(Self.ext)) }
            if force || a.smap != n.smap { set("slab-smap", n.smap.map(Self.ext)) }
            if force || a.grace != n.grace { set("slab-grace", n.grace.map(Self.ext)) }
            if force || a.posts != n.posts { set("posts", n.posts.map(Self.ext)) }
            if force || a.shadow != n.shadow { set("shadow", n.shadow.map { Self.poly($0) }) }
            applied = n
        }

        // MARK: camera

        private func camera(_ map: MLNMapView, center: CLLocationCoordinate2D, zoom: Double, pitch: Double, heading: Double) -> MLNMapCamera {
            let alt = MLNAltitudeForZoomLevel(zoom, pitch, center.latitude, map.bounds.size)
            return MLNMapCamera(lookingAtCenter: center, altitude: alt, pitch: pitch, heading: heading)
        }

        private func fly(_ cam: MLNMapCamera, seconds: Double) {
            guard let map else { return }
            if reduceMotion || seconds == 0 { map.setCamera(cam, animated: false) }
            else { map.setCamera(cam, withDuration: seconds, animationTimingFunction: CAMediaTimingFunction(name: .easeInEaseOut)) }
        }

        func run(_ cmd: MapCommand) {
            guard let map, loaded else { pending = cmd; return }
            switch cmd.kind {
            case .home:
                fly(camera(map, center: .init(latitude: Map3D.homeLat, longitude: Map3D.homeLon), zoom: Map3D.homeZoom, pitch: 0, heading: 0), seconds: 1.5)
            case let .card(bounds, lat, lon):
                var zoom = 10.6
                if let b = bounds, b.count == 4 {
                    let span = max(b[2] - b[0], (b[3] - b[1]), 0.004) * 4
                    zoom = max(8, min(13, log2(360 * Double(map.bounds.width) / 256 / span / 1.2)))
                }
                fly(camera(map, center: .init(latitude: lat, longitude: lon), zoom: zoom, pitch: 0, heading: 0), seconds: 1.4)
            case let .drill(lat, lon, small):
                fly(camera(map, center: .init(latitude: lat - (small ? 0.0006 : 0.001), longitude: lon), zoom: small ? 15.15 : 14.5, pitch: 60, heading: -24), seconds: 1.8)
            }
        }

        // MARK: delegate

        private func report() {
            guard let map else { return }
            onCamera(CameraState(zoom: map.zoomLevel, pitch: map.camera.pitch, heading: map.camera.heading))
        }

        func mapView(_ mapView: MLNMapView, regionDidChangeWith reason: MLNCameraChangeReason, animated: Bool) {
            report()
            // After a pinch or zoom gesture ends, let the tilt catch up with the zoom. Never inside the gesture.
            let gesture: MLNCameraChangeReason = [.gesturePinch, .gestureZoomIn, .gestureZoomOut, .gestureOneFingerZoom]
            guard !reason.isDisjoint(with: gesture), let focus else { return }
            let p = mapView.convert(focus, toPointTo: mapView)
            guard mapView.bounds.insetBy(dx: -64, dy: -64).contains(p) else { return }
            let f = Map3D.zoomFraction(mapView.zoomLevel)
            let cam = mapView.camera
            let pitch = Map3D.pitch(forFraction: f), heading = Map3D.bearing(forFraction: f)
            guard abs(cam.pitch - pitch) > 1 || (f > 0 && abs(cam.heading - heading) > 1) else { return }
            let next = camera(mapView, center: mapView.centerCoordinate, zoom: mapView.zoomLevel, pitch: pitch, heading: f > 0 ? heading : cam.heading)
            fly(next, seconds: 0.35)
        }

        @objc func tapped(_ g: UITapGestureRecognizer) {
            guard let map else { return }
            let pt = g.location(in: map)
            let box = CGRect(x: pt.x - 22, y: pt.y - 22, width: 44, height: 44)
            let hits = map.visibleFeatures(in: box, styleLayerIdentifiers: ["pins", "field-hit"])
            if let id = hits.compactMap({ $0.attribute(forKey: "id") as? String }).first { onSelect(id) }
        }
    }
}
