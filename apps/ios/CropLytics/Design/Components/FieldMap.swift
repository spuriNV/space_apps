import SwiftUI
import MapKit

/// The field on satellite imagery with its outline in the selection yellow (MapKit, `.imagery` style).
struct FieldMap: View {
    let field: FieldLocation
    var height: CGFloat = 190
    var interactive = false

    var body: some View {
        Map(initialPosition: .region(FieldMapRegion.region(for: field, padding: 2.2)), interactionModes: interactive ? .all : []) {
            ForEach(Array((field.geometry?.rings ?? []).enumerated()), id: \.offset) { _, ring in
                MapPolygon(coordinates: ring)
                    .stroke(Palette.fieldOutline, style: StrokeStyle(lineWidth: 2.5, lineJoin: .round))
                    .foregroundStyle(.clear)
            }
            if field.geometry == nil {
                Marker(FieldNaming.displayName(field), coordinate: field.centroid.clCoordinate)
            }
        }
        .mapStyle(.imagery(elevation: .flat))
        .mapControlVisibility(.hidden)
        .frame(height: height)
        .clipShape(RoundedRectangle(cornerRadius: Metrics.radius))
        .overlay(RoundedRectangle(cornerRadius: Metrics.radius).strokeBorder(Palette.line))
        .accessibilityElement()
        .accessibilityLabel("Satellite map of \(FieldNaming.displayName(field)), outlined in yellow")
        .accessibilityAddTraits(.isImage)
    }
}

/// The field's name the way the grower says it, then acres, crop and county; the state ID small.
struct FieldHeader: View {
    let field: FieldLocation
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(FieldNaming.displayName(field))
                .font(.clTitle)
                .foregroundStyle(Palette.text)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            Text(FieldNaming.subtitle(field))
                .font(.clBody)
                .foregroundStyle(Palette.text2)
            if let dwr = field.dwrUniqueId {
                Text("State field no. \(dwr) · \(String(format: "%.4f° N, %.4f° W", field.centroid.lat, abs(field.centroid.lon)))")
                    .font(.clCite)
                    .foregroundStyle(Palette.muted)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

/// Thumbnail for the field list: MapKit snapshot, or a quiet placeholder while it draws.
struct FieldThumbnail: View {
    let field: FieldLocation
    @Environment(AppEnvironment.self) private var env

    var body: some View {
        ZStack {
            Rectangle().fill(Palette.panel2)
            if let img = env.thumbnails.image(for: field.id) {
                Image(uiImage: img).resizable().scaledToFill()
            } else {
                Image(systemName: "map").foregroundStyle(Palette.muted)
            }
        }
        .frame(width: 84, height: 63)
        .clipShape(RoundedRectangle(cornerRadius: 3))
        .overlay(RoundedRectangle(cornerRadius: 3).strokeBorder(Palette.line))
        .task(id: field.id) { await env.thumbnails.load(field) }
        .accessibilityHidden(true)
    }
}
