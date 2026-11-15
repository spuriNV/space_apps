import SwiftUI

/// Paper top bar: the wordmark (back to all of California), the field switcher, and a menu. A 3pt spot-green band under it.
struct TopBar: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        @Bindable var app = app
        VStack(spacing: 0) {
            HStack(spacing: 0) {
                Button { app.goHome() } label: {
                    Text("CropLytics").font(.clWordmark).foregroundStyle(Palette.accent)
                        .padding(.horizontal, 12).frame(minHeight: 44)
                }
                .buttonStyle(.plain)
                .accessibilityHint("Back to all of California")
                .accessibilityIdentifier("wordmark")

                Rectangle().fill(Palette.line).frame(width: 1, height: 32)

                Button { app.showPicker() } label: {
                    HStack(spacing: 6) {
                        VStack(alignment: .leading, spacing: 1) {
                            Text(app.selectedField.map { "\(FieldNaming.place($0)), \(FieldNaming.acres($0)) acres" } ?? "No field picked")
                                .font(.clCite).foregroundStyle(Palette.muted).lineLimit(1)
                            Text(app.selectedField.map(FieldNaming.displayName) ?? "Pick your field")
                                .font(.custom(FontName.slabSemibold, size: 16, relativeTo: .headline)).foregroundStyle(Palette.text).lineLimit(1)
                        }
                        Spacer(minLength: 4)
                        Image(systemName: "chevron.down").font(.system(size: 13, weight: .semibold)).foregroundStyle(Palette.text2)
                    }
                    .padding(.horizontal, 10)
                    .frame(maxWidth: .infinity, minHeight: 44)
                    .contentShape(Rectangle())
                }
                .buttonStyle(StateLayerStyle(shape: Rectangle()))
                .accessibilityLabel(app.selectedField.map { "Field: \(FieldNaming.displayName($0)). Change field" } ?? "Pick your field")
                .accessibilityIdentifier("field-switch")

                Rectangle().fill(Palette.line).frame(width: 1, height: 32)

                Menu {
                    Button { app.dateOpen = true } label: { Label("Viewing: \(app.isToday ? "today" : app.t.label)", systemImage: "calendar") }
                    Button { app.layersOpen = true } label: { Label("Map layers", systemImage: "square.3.layers.3d") }
                    Toggle(isOn: $app.detailOn) { Label("More detail everywhere", systemImage: "text.magnifyingglass") }
                    Button { app.sourcesOpen = true } label: { Label("Sources", systemImage: "books.vertical") }
                    Divider()
                    Button { app.goHome() } label: { Label("Whole of California", systemImage: "house") }
                } label: {
                    Image(systemName: "line.3.horizontal").font(.system(size: 19, weight: .semibold)).foregroundStyle(Palette.text)
                        .frame(width: 52, height: 44).contentShape(Rectangle())
                }
                .accessibilityLabel("Menu")
                .accessibilityIdentifier("menu")
            }
            .frame(height: Metrics.topBar)
            .background(Palette.paper)
            Rectangle().fill(Palette.band).frame(height: 3)
        }
        .background(Palette.paper.ignoresSafeArea(edges: .top))
        .elevation1()
    }
}

/// Bottom tabs with a tonal pill on the active one (Material navigation-bar indicator); disabled until a field is picked.
struct TabBar: View {
    @Environment(AppModel.self) private var app
    @Namespace private var ns
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        HStack(spacing: 0) {
            ForEach(AppTab.allCases, id: \.self) { tab in
                let on = app.selectedField != nil && !app.pickerOpen && app.tab == tab
                let enabled = app.selectedField != nil
                Button {
                    withAnimation(Motion.std(reduce)) { app.select(tab: tab) }
                } label: {
                    Text(tab.title)
                        .font(.clLabel)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                        .foregroundStyle(on ? Palette.onAccentContainer : Palette.text2)
                        .padding(.horizontal, 9).frame(height: 32)
                        .background {
                            if on { Capsule().fill(Palette.accentContainer).matchedGeometryEffect(id: "tab-pill", in: ns) }
                        }
                        .frame(maxWidth: .infinity, minHeight: 48)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .disabled(!enabled)
                .opacity(enabled ? 1 : 0.45)
                .accessibilityLabel(tab.longTitle)
                .accessibilityAddTraits(on ? .isSelected : [])
                .accessibilityIdentifier("tab-\(tab.rawValue)")
            }
        }
        .padding(.horizontal, 6)
        .overlay(alignment: .top) { Hairline() }
    }
}

/// Over the map: the viewing date (with "Back to today"), map layers, home, and the 3D look under the field.
struct MapOverlayControls: View {
    @Environment(AppModel.self) private var app
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            VStack(alignment: .leading, spacing: 8) {
                Button { app.dateOpen = true } label: {
                    HStack(spacing: 6) {
                        Image(systemName: app.playing ? "play.fill" : "calendar").font(.system(size: 13, weight: .semibold))
                        Text(app.isToday ? "Today, \(app.t.label)" : "Showing \(app.t.label)")
                            .font(.clLabel).contentTransition(.numericText())
                        Image(systemName: "chevron.down").font(.system(size: 11, weight: .bold))
                    }
                    .foregroundStyle(Palette.text)
                    .padding(.horizontal, 14).frame(height: 36)
                    .background(Capsule().fill(Palette.paper)).elevation2()
                }
                .buttonStyle(.plain)
                .accessibilityLabel(app.isToday ? "Viewing today. Change date" : "Viewing \(app.t.label). Change date")
                .accessibilityIdentifier("date-control")
                if !app.isToday {
                    Button("Back to today") { withAnimation(Motion.std(reduce)) { app.backToToday() } }
                        .buttonStyle(.pill(.tonal, small: true))
                        .elevation1()
                        .accessibilityIdentifier("back-to-today")
                }
            }
            Spacer()
            VStack(spacing: 8) {
                mapButton("square.3.layers.3d", "Map layers") { app.layersOpen = true }
                mapButton("house", "Whole of California") { app.goHome() }
                if app.selectedField != nil {
                    mapButton("cube", "Look under the field in 3D") { app.drillOpen = true }
                        .accessibilityIdentifier("open-3d")
                }
            }
        }
        .padding(.horizontal, 12)
    }

    private func mapButton(_ symbol: String, _ label: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: symbol).font(.system(size: 17, weight: .semibold)).foregroundStyle(Palette.text)
                .frame(width: 44, height: 44)
                .background(Circle().fill(Palette.paper)).elevation2()
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }
}

/// The field's name the way the grower says it, fact chips, and the id line; compresses to one line when scrolled.
struct FieldHeader: View {
    let field: FieldLocation
    var stuck: Bool
    @Environment(AppModel.self) private var app

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            VStack(alignment: .leading, spacing: stuck ? 4 : 8) {
                Text(FieldNaming.displayName(field))
                    .font(stuck ? .custom(FontName.slabSemibold, size: 19, relativeTo: .headline) : .clTitlePhone)
                    .foregroundStyle(Palette.text)
                    .lineLimit(stuck ? 1 : 3)
                    .accessibilityAddTraits(.isHeader)
                    .accessibilityIdentifier("field-title")
                if stuck {
                    Text(FieldNaming.subtitle(field)).font(.clSecondary).foregroundStyle(Palette.text2).lineLimit(1)
                } else {
                    FlowLayout(spacing: 6) {
                        FactChip(text: Text("\(FieldNaming.acres(field))").bold() + Text(" acres"))
                        if let latest = FieldNaming.latestCrop(field.cropHistory) {
                            FactChip(dot: DataColor.crop(latest.crop), text: Text("\(latest.crop) in \(String(latest.year))"))
                        }
                        FactChip(text: Text(FieldNaming.place(field)))
                    }
                    Text(FieldNaming.idLine(field)).font(.clCite).foregroundStyle(Palette.muted).lineLimit(1)
                }
            }
            Spacer(minLength: 0)
            IconButton(systemName: "xmark", label: "Close") { app.showPicker() }
                .accessibilityIdentifier("close-field")
        }
        .padding(.horizontal, Metrics.gutter)
        .padding(.top, 2)
        .padding(.bottom, stuck ? 8 : 12)
    }
}
