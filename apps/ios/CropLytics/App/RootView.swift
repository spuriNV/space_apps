import SwiftUI

/// Tabs along the bottom (the iOS pattern for 3-5 peer sections); each tab has its own NavigationStack.
struct RootView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        TabView(selection: $model.tab) {
            NavigationStack { FieldsScreen() }
                .tabItem { Label(AppTab.fields.title, systemImage: AppTab.fields.symbol) }
                .tag(AppTab.fields)

            FieldTab(tab: .now) { FieldNowScreen(field: $0) }
                .tabItem { Label(AppTab.now.title, systemImage: AppTab.now.symbol) }
                .tag(AppTab.now)

            FieldTab(tab: .season) { ComingSeasonScreen(field: $0) }
                .tabItem { Label(AppTab.season.title, systemImage: AppTab.season.symbol) }
                .tag(AppTab.season)

            FieldTab(tab: .compare) { CompareScreen(field: $0) }
                .tabItem { Label(AppTab.compare.title, systemImage: AppTab.compare.symbol) }
                .tag(AppTab.compare)

            FieldTab(tab: .summary) { SummaryScreen(field: $0) }
                .tabItem { Label(AppTab.summary.title, systemImage: AppTab.summary.symbol) }
                .tag(AppTab.summary)
        }
        .task { await model.loadFields() }
    }
}

/// A tab about the chosen field: its own NavigationStack, a field switcher, and a prompt when no field is chosen yet.
struct FieldTab<Content: View>: View {
    let tab: AppTab
    @ViewBuilder let content: (FieldLocation) -> Content
    @Environment(AppModel.self) private var model

    var body: some View {
        NavigationStack {
            Group {
                if let field = model.selectedField {
                    content(field)
                        .id(field.id)
                } else if model.fields.isLoading && model.selectedFieldID != nil {
                    ProgressView("Loading your field")
                        .font(.clBody)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if case .failed(let error) = model.fields {
                    ErrorStateView(error: error) { Task { await model.loadFields() } }
                } else {
                    ContentUnavailableView {
                        Label("Pick a field first", systemImage: "square.grid.2x2")
                    } description: {
                        Text("Choose one of your fields to see \(tab.title.lowercased()).")
                    } actions: {
                        Button("See your fields") { model.tab = .fields }
                            .buttonStyle(.borderedProminent)
                    }
                }
            }
            .background(Palette.paper)
            .navigationTitle(tab.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if model.selectedField != nil {
                    ToolbarItem(placement: .topBarTrailing) { FieldSwitcher() }
                }
            }
            .wakingBanner()
        }
    }
}

/// "Change field": a menu listing the grower's fields.
struct FieldSwitcher: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        Menu {
            ForEach(model.fields.value ?? []) { field in
                Button {
                    model.select(field.id)
                } label: {
                    if field.id == model.selectedFieldID {
                        Label(FieldNaming.displayName(field), systemImage: "checkmark")
                    } else {
                        Text(FieldNaming.displayName(field))
                    }
                }
            }
        } label: {
            Label("Change field", systemImage: "arrow.triangle.swap")
        }
        .accessibilityIdentifier("change-field")
    }
}
