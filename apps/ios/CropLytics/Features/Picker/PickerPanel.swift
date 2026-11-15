import SwiftUI
import Observation

/// "Pick your field": search, Rice / Forage / British Columbia chips, one row per field with a satellite thumbnail
/// (outline drawn), facts in grower units, what's notable, and 2023-2026 season strips. BC fields sit under their own heading.
struct PickerPanel: View {
    @Environment(AppModel.self) private var app
    @Environment(AppEnvironment.self) private var env
    @State private var query = ""
    @State private var family: String?
    @State private var strips: StripStore?

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Pick your field").font(.clHeading).foregroundStyle(Palette.text).accessibilityAddTraits(.isHeader)
                Spacer()
                if app.session != nil {
                    IconButton(systemName: "xmark", label: "Close") { app.pickerOpen = false }
                }
            }
            .padding(.horizontal, Metrics.gutter).padding(.bottom, 8)

            switch app.fields {
            case .idle, .loading:
                VStack(spacing: 12) { ForEach(0..<3, id: \.self) { _ in PlaceholderRow() } }
                    .padding(.horizontal, Metrics.gutter).placeholder(true)
                Spacer(minLength: 0)
            case .failed(let e):
                ErrorStateView(error: e) { Task { await app.loadFields() } }
                Spacer(minLength: 0)
            case .loaded(let fields, let freshness):
                list(fields, freshness)
            }
        }
        .task(id: app.fields.value?.count) {
            if strips == nil { strips = StripStore(repository: env.repository) }
        }
    }

    private func list(_ fields: [FieldLocation], _ freshness: Freshness) -> some View {
        let families: [(String, String, Int)] = [("rice", "Rice"), ("forage", "Forage"), ("bc", "British Columbia")].map { f, label in
            (f, label, fields.filter { f == "bc" ? $0.isBC : (!$0.isBC && $0.family == f) }.count)
        }.filter { $0.2 > 0 }
        let shown = Self.filter(fields, query: query, family: family)
        let ca = shown.filter { !$0.isBC }, bc = shown.filter(\.isBC)
        return VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass").foregroundStyle(Palette.muted)
                TextField("Search by town, county or crop", text: $query)
                    .font(.clBody).textInputAutocapitalization(.never).autocorrectionDisabled()
                    .accessibilityIdentifier("pk-search")
                if !query.isEmpty {
                    Button { query = "" } label: { Image(systemName: "xmark.circle.fill").foregroundStyle(Palette.muted) }
                        .accessibilityLabel("Clear search")
                }
            }
            .padding(.horizontal, 16).frame(height: 48)
            .background(Capsule().fill(Palette.panel2))
            .overlay(Capsule().strokeBorder(Palette.lineSoft))
            .padding(.horizontal, Metrics.gutter)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(families, id: \.0) { f, label, n in
                        FilterChip(title: label, count: n, isOn: family == f) { family = family == f ? nil : f }
                            .accessibilityIdentifier("chip-\(f)")
                    }
                }
                .padding(.horizontal, Metrics.gutter)
            }

            SheetScroll(stuck: .constant(false)) {
                VStack(alignment: .leading, spacing: 2) {
                    ForEach(ca) { f in row(f) }
                    if !bc.isEmpty {
                        Text("British Columbia").font(.clHeading).padding(.top, 16).padding(.bottom, 4)
                            .accessibilityAddTraits(.isHeader).accessibilityIdentifier("pk-group-bc")
                        ForEach(bc) { f in row(f) }
                    }
                    if shown.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("No field matches.").font(.clBody).foregroundStyle(Palette.muted)
                            Button("Show all") { query = ""; family = nil }.buttonStyle(.pill(.outline, small: true))
                        }
                        .padding(.top, 12)
                    }
                    SavedNote(freshness: freshness).padding(.top, 8)
                }
                .padding(.horizontal, -4)
            }
        }
    }

    private func row(_ f: FieldLocation) -> some View {
        PickerRow(field: f, current: f.id == app.selectedField?.id, strips: strips) { app.open(f.id, tab: .now) }
    }

    /// Every word must match the name, place, region, crop or water district.
    static func filter(_ fields: [FieldLocation], query: String, family: String?) -> [FieldLocation] {
        let words = query.lowercased().split(whereSeparator: \.isWhitespace).map(String.init)
        return fields.filter { f in
            if let family, family == "bc" ? !f.isBC : (f.isBC || f.family != family) { return false }
            let hay = "\(FieldNaming.displayName(f)) \(FieldNaming.place(f)) \(f.isBC ? "british columbia bc" : "county california") \(FieldNaming.latestCrop(f.cropHistory)?.crop ?? "") \(f.water?.district ?? "")".lowercased()
            return words.allSatisfy { hay.range(of: $0, options: .diacriticInsensitive) != nil }
        }
    }
}

private struct PickerRow: View {
    let field: FieldLocation
    let current: Bool
    let strips: StripStore?
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(alignment: .top, spacing: 14) {
                FieldThumbnail(field: field, current: current)
                VStack(alignment: .leading, spacing: 4) {
                    Text(FieldNaming.displayName(field)).font(.clRowTitle).foregroundStyle(current ? Palette.onAccentContainer : Palette.text)
                        .multilineTextAlignment(.leading).fixedSize(horizontal: false, vertical: true)
                    Text("\(FieldNaming.place(field)) · \(FieldNaming.acres(field)) acres · \(FieldNaming.latestCrop(field.cropHistory).map { "\($0.crop.lowercased()) in \($0.year)" } ?? "")")
                        .font(.clSecondary).foregroundStyle(Palette.text2).multilineTextAlignment(.leading)
                    let note = FieldNaming.notable(field)
                    if !note.isEmpty { Text(note).font(.clCite).foregroundStyle(Palette.muted).multilineTextAlignment(.leading) }
                    YearStrips(fieldID: field.id, strips: strips)
                }
                Spacer(minLength: 0)
            }
            .padding(12)
            .background(RoundedRectangle(cornerRadius: Radius.md, style: .continuous).fill(current ? Palette.accentContainer : .clear))
            .contentShape(RoundedRectangle(cornerRadius: Radius.md, style: .continuous))
        }
        .buttonStyle(StateLayerStyle(shape: RoundedRectangle(cornerRadius: Radius.md, style: .continuous)))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(FieldNaming.displayName(field)). \(FieldNaming.acres(field)) acres, \(FieldNaming.place(field)). \(FieldNaming.cropLine(field)).")
        .accessibilityAddTraits(current ? [.isButton, .isSelected] : .isButton)
        .accessibilityIdentifier("field-\(field.id)")
    }
}

/// 2023-2026 strips for a pick-list row, loaded as the row appears.
private struct YearStrips: View {
    let fieldID: String
    let strips: StripStore?
    var body: some View {
        let years = strips?.years(for: fieldID)
        HStack(spacing: 6) {
            ForEach(StripStore.shownYears, id: \.self) { y in
                VStack(spacing: 2) {
                    SeasonStripView(classes: years?[y] ?? Array(repeating: .noView, count: 36), height: 7)
                    Text(String(y)).font(.clCite).foregroundStyle(Palette.muted)
                }
            }
        }
        .padding(.top, 2)
        .task(id: fieldID) { await strips?.load(fieldID) }
        .accessibilityHidden(true)
    }
}

/// Season strips per field for the pick list (one calendar request per field, saved on the phone).
@MainActor
@Observable
final class StripStore {
    static var shownYears: [Int] { let y = GrowerDate.year(.now); return Array((y - 3)...y) }
    private var byField: [String: [Int: [CoverClass]]] = [:]
    private var pending: Set<String> = []
    private let repository: any FieldRepository

    init(repository: any FieldRepository) { self.repository = repository }

    func years(for id: String) -> [Int: [CoverClass]]? { byField[id] }

    func load(_ id: String) async {
        guard byField[id] == nil, !pending.contains(id) else { return }
        pending.insert(id)
        defer { pending.remove(id) }
        var state: LoadState<FieldCalendar> = .idle
        await consume(repository.calendar(id)) { state = $0 }
        if let cal = state.value {
            byField[id] = Dictionary(uniqueKeysWithValues: Self.shownYears.map { ($0, cal.classes(for: $0)) })
        }
    }
}

/// Satellite thumbnail with the outline; the current field gets a paper gap and a green ring.
struct FieldThumbnail: View {
    let field: FieldLocation
    var current = false
    var size = CGSize(width: 88, height: 60)
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
        .frame(width: size.width, height: size.height)
        .clipShape(RoundedRectangle(cornerRadius: Radius.sm, style: .continuous))
        .padding(current ? 2 : 0)
        .overlay {
            if current { RoundedRectangle(cornerRadius: Radius.sm + 2, style: .continuous).strokeBorder(Palette.accentOutline, lineWidth: 2) }
        }
        .task(id: field.id) { await env.thumbnails.load(field, size: CGSize(width: 132, height: 90)) }
        .accessibilityHidden(true)
    }
}

private struct PlaceholderRow: View {
    var body: some View {
        HStack(spacing: 14) {
            RoundedRectangle(cornerRadius: Radius.sm).fill(Palette.panel2).frame(width: 88, height: 60)
            VStack(alignment: .leading, spacing: 4) {
                Text("Rice field 4 miles east of Williams").font(.clRowTitle)
                Text("Colusa County · 149 acres · rice in 2025").font(.clSecondary)
            }
        }
    }
}
