import SwiftUI
import MapLibre

/// The full interactive satellite map (MapLibre Native, the same style as Android): a pin and outline for every field,
/// the open field in the selection yellow tinted by what the satellites saw at the viewing date, the NASA footprints,
/// and the 3D stack (30 m cover cells, soil-moisture slab, groundwater slab) that rises as you zoom in.
struct FieldsMap: View {
    let bottomInset: CGFloat
    let topInset: CGFloat
    @Environment(AppModel.self) private var app
    @Environment(\.accessibilityReduceMotion) private var reduce
    @State private var command = MapCommand()
    @State private var camera = CameraState()
    @State private var stack: Map3D.Stack?

    var body: some View {
        MapLibreView(content: content, command: command, topInset: topInset + 60, bottomInset: bottomInset, reduceMotion: reduce,
                     focus: app.selectedField?.centroid.clCoordinate,
                     onSelect: { id in withAnimation(Motion.std(reduce)) { app.open(id) } },
                     onCamera: { if $0 != camera { camera = $0 } })
            .ignoresSafeArea()
            .overlay(alignment: .topLeading) { if drilled, let st = stack { legend(st) } }
            .overlay(alignment: .bottomLeading) {
                Color.clear.frame(width: 1, height: 1).accessibilityElement()
                    .accessibilityLabel(String(format: "zoom %.1f pitch %.0f", camera.zoom, camera.pitch))
                    .accessibilityIdentifier("map-state")
            }
            .onChange(of: app.cameraRequest) { fly() }
            .onChange(of: app.drillOpen) { _, on in if on { app.drillOpen = false; drill() } }
            .onChange(of: app.layers) { _, l in
                if l.contains(.reserves) { Task { await app.session?.loadReserves() } }
            }
            .onAppear { if app.selectedField != nil { fly() }; if app.drillOpen { app.drillOpen = false; drill() } }
            .onChange(of: app.selectedField?.id) { _, id in if id != nil { fly() } }
            .task(id: app.selectedField?.id) { await app.session?.loadGrid() }
            .task(id: stackKey) { stack = buildStack() }
    }

    private var drilled: Bool { Map3D.isDrilled(zoom: camera.zoom, fieldOpen: app.selectedField != nil) }

    // MARK: content

    private var content: MapContent {
        var c = MapContent()
        let selected = app.selectedField
        let tint = selectedClass.map { Self.hex(SeasonStripView.color($0)) } ?? "rgba(0,0,0,0)"
        for f in app.fields.value ?? [] {
            let isSel = f.id == selected?.id
            c.pins.append(.init(id: f.id, name: FieldNaming.displayName(f), lon: f.centroid.lon, lat: f.centroid.lat, selected: isSel))
            if isSel || app.layers.contains(.outlines) {
                for ring in f.geometry?.rings ?? [] { c.outlines.append(.init(id: f.id, ring: ring.map { [$0.longitude, $0.latitude] }, selected: isSel, tint: tint)) }
            }
        }
        if let f = selected {
            for layer in MapLayer.allCases where app.layers.contains(layer) {
                guard let d = layer.footprintDegrees else { continue }
                let sq = footprint(f, d)
                c.footprints.append(.init(ring: (sq + [sq[0]]).map { [$0.longitude, $0.latitude] },
                                          color: layer == .grace ? "#F29BD0" : layer == .smap ? "#7FB8FF" : "#BDE3A0"))
            }
            if f.isBC, app.layers.contains(.reserves), let o = app.session?.reserves.value?.outlines {
                c.reserves = o.flatMap(\.rings).map { $0.map { [$0.longitude, $0.latitude] } }
            }
        }
        if let st = stack {
            c.cells = st.cells; c.smap = st.smap; c.grace = st.grace; c.posts = st.posts; c.shadow = st.shadow
        }
        return c
    }

    private static func hex(_ color: Color) -> String {
        let u = UIColor(color)
        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        u.getRed(&r, green: &g, blue: &b, alpha: &a)
        return String(format: "#%02X%02X%02X", Int(r * 255), Int(g * 255), Int(b * 255))
    }

    /// What the satellites saw on the open field at the viewing date (replay colours the field).
    private var selectedClass: CoverClass? {
        guard let cal = app.session?.calendar.value else { return nil }
        let c = cal.classes(for: app.t.year)[app.t.dekad]
        return c == .noView ? nil : c
    }

    // MARK: 3D stack

    private var soilPct: Double? {
        if let r = app.session?.nasaNow.value?.reading("smap_rootzone_pct")?.value ?? app.session?.nasaNow.value?.reading("grace_rootzone_pct")?.value, app.isToday { return r }
        return app.session?.daily.value.flatMap { DailyAnalysis.readings($0, at: app.t).soil?.0 }
    }
    private var gwPct: Double? {
        if app.isToday, let r = app.session?.nasaNow.value?.reading("grace_gw_pct")?.value { return r }
        return app.session?.daily.value.flatMap { DailyAnalysis.readings($0, at: app.t).groundwater?.0 }
    }

    private var stackKey: String {
        guard let f = app.selectedField else { return "none" }
        return "\(f.id)|\(app.session?.grid.value?.cells.count ?? -1)|\(Map3D.quarterKey(year: app.t.year, month: app.t.month))|\(soilPct ?? -1)|\(gwPct ?? -1)"
    }

    private func buildStack() -> Map3D.Stack? {
        guard let f = app.selectedField, let rings = f.geometry?.rings, !rings.isEmpty else { return nil }
        let r = rings.map { $0.map { (lon: $0.longitude, lat: $0.latitude) } }
        let cells = (app.session?.grid.value?.cells ?? []).filter { $0.inField >= 0.5 }.map { c in
            (ring: c.ring.map { (lon: $0.longitude, lat: $0.latitude) }, ndvi: Map3D.ndvi(c.ndvi, year: app.t.year, month: app.t.month))
        }
        return Map3D.stack(rings: r, lat: f.centroid.lat, cells: cells, soilPct: soilPct, groundwaterPct: gwPct)
    }

    private func legend(_ st: Map3D.Stack) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            MapLabel(text: "Crop: 100 ft squares, taller is greener")
            MapLabel(text: "Soil moisture: \(st.soilWords)")
            MapLabel(text: "Groundwater: \(st.groundwaterWords)")
        }
        .padding(.leading, 12).padding(.top, topInset + 64)
        .allowsHitTesting(false)
    }

    // MARK: camera

    private func fly() {
        if let f = app.selectedField, !app.homeRequested {
            let b = f.geometry?.bounds.map { [$0.minLon, $0.minLat, $0.maxLon, $0.maxLat] }
            command = MapCommand(id: command.id + 1, kind: .card(bounds: b, lat: f.centroid.lat, lon: f.centroid.lon))
        } else {
            command = MapCommand(id: command.id + 1, kind: .home)
        }
    }

    private func drill() {
        guard let f = app.selectedField else { return }
        let small = (f.areaHa?.value ?? 100) < 45
        command = MapCommand(id: command.id + 1, kind: .drill(lat: f.centroid.lat, lon: f.centroid.lon, small: small))
    }

    private func footprint(_ f: FieldLocation, _ deg: Double) -> [CLLocationCoordinate2D] {
        // the grid cell containing the field centre
        let lat0 = (f.centroid.lat / deg).rounded(.down) * deg, lon0 = (f.centroid.lon / deg).rounded(.down) * deg
        return [.init(latitude: lat0, longitude: lon0), .init(latitude: lat0 + deg, longitude: lon0),
                .init(latitude: lat0 + deg, longitude: lon0 + deg), .init(latitude: lat0, longitude: lon0 + deg)]
    }
}

/// Map label: solid paper box, 1px ink border, small shadow (the skill's rule for text over imagery).
struct MapLabel: View {
    let text: String
    var body: some View {
        Text(text).font(.clCiteStrong).foregroundStyle(Color(hex: 0x191C16)).lineLimit(1)
            .padding(.horizontal, 6).padding(.vertical, 3)
            .background(Color(hex: 0xF7F6F0))
            .overlay(Rectangle().strokeBorder(Color(hex: 0x191C16), lineWidth: 1))
            .shadow(color: .black.opacity(0.3), radius: 1, y: 1)
    }
}
