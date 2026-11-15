import SwiftUI

/// "Pick your field": a list a grower recognises, with satellite thumbnails, searchable.
struct FieldsScreen: View {
    @Environment(AppModel.self) private var app
    @State private var model: FieldsViewModel?

    var body: some View {
        Group {
            if let model { FieldsList(model: model) } else { Color.clear }
        }
        .navigationTitle("Your fields")
        .navigationBarTitleDisplayMode(.large)
        .wakingBanner()
        .onAppear { if model == nil { model = FieldsViewModel(app: app) } }
    }
}

private struct FieldsList: View {
    @Bindable var model: FieldsViewModel
    @Environment(AppModel.self) private var app

    var body: some View {
        List {
            switch model.state {
            case .idle, .loading:
                Section {
                    ForEach(0..<4, id: \.self) { _ in PlaceholderRow() }
                }
                .placeholder(true)
            case .failed(let error):
                ErrorStateView(error: error) { Task { await model.refresh() } }
                    .listRowBackground(Color.clear)
            case .loaded(_, let freshness):
                Section {
                    ForEach(model.rows) { row in
                        if let field = app.fields.value?.first(where: { $0.id == row.id }) {
                            Button { model.open(row.id) } label: { FieldRowView(row: row, field: field) }
                                .buttonStyle(.plain)
                                .accessibilityIdentifier("field-\(row.id)")
                        }
                    }
                } header: {
                    Text("California fields with NASA satellite records")
                        .font(.clSecondary)
                        .foregroundStyle(Palette.muted)
                        .textCase(nil)
                } footer: {
                    VStack(alignment: .leading, spacing: 8) {
                        SavedNote(freshness: freshness)
                        Text("Why not British Columbia yet? BC doesn't have the ground records needed to check a tool like this, so we built and checked it where the data is rich first.")
                            .font(.clCite)
                            .foregroundStyle(Palette.muted)
                    }
                    .padding(.top, 6)
                }
                if model.rows.isEmpty {
                    ContentUnavailableView.search(text: model.searchText)
                        .listRowBackground(Color.clear)
                }
            }
        }
        .listStyle(.insetGrouped)
        .scrollContentBackground(.hidden)
        .background(Palette.paper)
        .searchable(text: $model.searchText, prompt: "Field, town, county or crop")
        .refreshable { await model.refresh() }
    }
}

private struct FieldRowView: View {
    let row: FieldRow
    let field: FieldLocation

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            FieldThumbnail(field: field)
            VStack(alignment: .leading, spacing: 3) {
                Text(row.name)
                    .font(.custom(FontName.slabSemibold, size: 18, relativeTo: .headline))
                    .foregroundStyle(Palette.text)
                    .fixedSize(horizontal: false, vertical: true)
                Text("\(row.county) County · \(row.acres) acres")
                    .font(.clSecondary)
                    .foregroundStyle(Palette.text2)
                HStack(spacing: 6) {
                    Circle().fill(DataColor.crop(FieldNaming.latestCrop(field.cropHistory)?.crop ?? "")).frame(width: 8, height: 8)
                    Text(row.crop).font(.clSecondary).foregroundStyle(Palette.text2)
                }
            }
            Spacer(minLength: 0)
            Image(systemName: "chevron.right").font(.footnote.weight(.semibold)).foregroundStyle(Palette.muted)
                .padding(.top, 4)
        }
        .padding(.vertical, 4)
        .contentShape(Rectangle())
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(row.accessibilityText)
        .accessibilityHint("Opens this field")
        .accessibilityAddTraits(.isButton)
    }
}

private struct PlaceholderRow: View {
    var body: some View {
        HStack(spacing: 12) {
            Rectangle().fill(Palette.panel2).frame(width: 84, height: 63)
            VStack(alignment: .leading, spacing: 4) {
                Text("Rice field 4 miles east of Williams").font(.clAnswer)
                Text("Colusa County · 149 acres").font(.clSecondary)
                Text("Rice in 2025").font(.clSecondary)
            }
        }
        .padding(.vertical, 4)
    }
}
