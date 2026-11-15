import SwiftUI
import MapKit

/// The full interactive satellite map: a pin and outline for every field, the open field in the selection yellow,
/// tinted by what the satellites saw at the viewing date (so replay plays on the map), and the NASA footprints.
struct FieldsMap: View {
    let bottomInset: CGFloat
    let topInset: CGFloat
    @Environment(AppModel.self) private var app
    @State private var position: MapCameraPosition = .region(FieldsMap.california)
    @Environment(\.accessibilityReduceMotion) private var reduce

    static let california = MKCoordinateRegion(center: .init(latitude: 37.4, longitude: -120.2), span: .init(latitudeDelta: 8.5, longitudeDelta: 8.5))

    var body: some View {
        let fields = app.fields.value ?? []
        let selected = app.selectedField
        let cls = selectedClass
        Map(position: $position, interactionModes: .all) {
            ForEach(fields) { f in
                let isSel = f.id == selected?.id
                if isSel || app.layers.contains(.outlines) {
                    ForEach(Array((f.geometry?.rings ?? []).enumerated()), id: \.offset) { _, ring in
                        if isSel {
                            MapPolygon(coordinates: ring)
                                .foregroundStyle(cls.map { SeasonStripView.color($0).opacity(0.45) } ?? Color.clear)
                                .stroke(Palette.fieldOutline, style: StrokeStyle(lineWidth: 3, lineJoin: .round))
                        } else {
                            MapPolygon(coordinates: ring)
                                .foregroundStyle(.clear)
                                .stroke(.white.opacity(0.8), style: StrokeStyle(lineWidth: 1.5, dash: [4, 3]))
                        }
                    }
                }
                Annotation(FieldNaming.displayName(f), coordinate: f.centroid.clCoordinate, anchor: .bottom) {
                    FieldPin(field: f, selected: isSel) { withAnimation(Motion.std(reduce)) { app.open(f.id) } }
                }
                .annotationTitles(.hidden)
            }
            if let f = selected {
                ForEach(MapLayer.allCases.filter { app.layers.contains($0) && $0.footprintDegrees != nil }, id: \.self) { layer in
                    MapPolygon(coordinates: footprint(f, layer.footprintDegrees!))
                        .foregroundStyle(.clear)
                        .stroke(layer == .grace ? Color(hex: 0xF29BD0) : layer == .smap ? Color(hex: 0x7FB8FF) : Color(hex: 0xBDE3A0),
                                style: StrokeStyle(lineWidth: 2, dash: [6, 4]))
                    Annotation(layer == .smap ? "Soil moisture: one reading covers this square" : layer == .grace ? "Groundwater: one reading for this square" : "Rain: one reading for this square",
                               coordinate: footprint(f, layer.footprintDegrees!)[1], anchor: .bottomLeading) {
                        MapLabel(text: layer == .smap ? "Soil moisture (NASA SMAP): one reading for this square" : layer == .grace ? "Groundwater (NASA GRACE-FO): one reading for this square" : "Rain (NASA IMERG): one reading for this square")
                    }
                    .annotationTitles(.hidden)
                }
                if f.isBC, app.layers.contains(.reserves), let outlines = app.session?.reserves.value?.outlines {
                    ForEach(outlines) { o in
                        ForEach(Array(o.rings.enumerated()), id: \.offset) { _, ring in
                            MapPolygon(coordinates: ring).foregroundStyle(Color(hex: 0xC77DFF).opacity(0.12))
                                .stroke(Color(hex: 0xC77DFF), style: StrokeStyle(lineWidth: 1.5, dash: [5, 3]))
                        }
                    }
                }
            }
        }
        .mapStyle(.imagery(elevation: .realistic))
        .mapControls {
            MapScaleView()
        }
        .safeAreaPadding(.top, topInset + 60)
        .safeAreaPadding(.bottom, bottomInset)
        .onChange(of: app.cameraRequest) { fly() }
        .onChange(of: app.layers) { _, l in
            if l.contains(.reserves) { Task { await app.session?.loadReserves() } }
        }
        .onAppear { if app.selectedField != nil { fly(animated: false) } }
        .onChange(of: app.selectedField?.id) { _, id in if id != nil { fly() } }
        .accessibilityLabel("Satellite map of the fields")
    }

    /// What the satellites saw on the open field at the viewing date (replay colours the field).
    private var selectedClass: CoverClass? {
        guard let cal = app.session?.calendar.value else { return nil }
        let c = cal.classes(for: app.t.year)[app.t.dekad]
        return c == .noView ? nil : c
    }

    private func fly(animated: Bool = true) {
        let target: MKCoordinateRegion
        if let f = app.selectedField, !app.homeRequested {
            target = FieldMapRegion.region(for: f, padding: 4)
        } else {
            target = Self.california
        }
        if animated && !reduce {
            withAnimation(.easeInOut(duration: 1.1)) { position = .region(target) }
        } else {
            position = .region(target)
        }
    }

    private func footprint(_ f: FieldLocation, _ deg: Double) -> [CLLocationCoordinate2D] {
        // the grid cell containing the field centre
        let lat0 = (f.centroid.lat / deg).rounded(.down) * deg, lon0 = (f.centroid.lon / deg).rounded(.down) * deg
        return [.init(latitude: lat0, longitude: lon0), .init(latitude: lat0 + deg, longitude: lon0),
                .init(latitude: lat0 + deg, longitude: lon0 + deg), .init(latitude: lat0, longitude: lon0 + deg)]
    }
}

/// A field pin: a green marker; the open field's name sits in a paper label box with an ink edge (never text on imagery).
struct FieldPin: View {
    let field: FieldLocation
    let selected: Bool
    let action: () -> Void
    @State private var bounce = false
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                if selected { MapLabel(text: FieldNaming.displayName(field)) }
                ZStack {
                    Circle().fill(selected ? Palette.band : Color(hex: 0x2F5D34).opacity(0.92)).frame(width: selected ? 30 : 24, height: selected ? 30 : 24)
                    Circle().strokeBorder(.white, lineWidth: 2).frame(width: selected ? 30 : 24, height: selected ? 30 : 24)
                    Image(systemName: field.family == "rice" ? "drop.fill" : "leaf.fill")
                        .font(.system(size: selected ? 13 : 10, weight: .bold)).foregroundStyle(.white)
                }
                .shadow(color: .black.opacity(0.5), radius: 2, y: 1)
                .offset(y: bounce ? -6 : 0)
            }
        }
        .buttonStyle(.plain)
        .frame(minWidth: 44, minHeight: 44)
        .onChange(of: selected) { _, s in
            guard s, !reduce else { return }
            withAnimation(.spring(response: 0.25, dampingFraction: 0.4)) { bounce = true }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) { withAnimation(.spring(response: 0.3, dampingFraction: 0.5)) { bounce = false } }
        }
        .accessibilityLabel(FieldNaming.displayName(field))
        .accessibilityHint(selected ? "The open field" : "Opens this field")
        .accessibilityIdentifier("pin-\(field.id)")
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
