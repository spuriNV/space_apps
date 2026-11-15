import SwiftUI

/// Map-first layout (web phone layout, redesign §5.2): the satellite map fills the screen; a paper top bar with the
/// field switcher; a non-modal bottom sheet (peek, half, full) with the pick list or the open section; a pill tab bar.
struct RootView: View {
    @Environment(AppModel.self) private var app
    @Environment(AppEnvironment.self) private var env
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        @Bindable var app = app
        GeometryReader { geo in
            let bottomSafe = geo.safeAreaInsets.bottom
            let topSafe = geo.safeAreaInsets.top
            let tabHeight = Metrics.tabBar + bottomSafe
            let sheetMax = geo.size.height + topSafe + bottomSafe - tabHeight - topSafe - Metrics.topBar - 3 - 8
            let visible = SheetGeometry.visibleHeight(app.detent, screen: geo.size.height + topSafe + bottomSafe, max: sheetMax)
            ZStack(alignment: .top) {
                FieldsMap(bottomInset: visible + tabHeight, topInset: topSafe + Metrics.topBar + 3)
                    .ignoresSafeArea()

                VStack(spacing: 8) {
                    MapOverlayControls()
                    if env.serverStatus.isWaking { WakingBanner().padding(.horizontal, 12).transition(.move(edge: .top).combined(with: .opacity)) }
                    Spacer()
                }
                .padding(.top, Metrics.topBar + 3 + 8)
                .animation(Motion.std(reduce, 0.24), value: env.serverStatus.isWaking)

                ZStack(alignment: .bottom) {
                    BottomSheet(detent: $app.detent, maxHeight: sheetMax, screenHeight: geo.size.height + topSafe + bottomSafe) {
                        SheetContent()
                    }
                    .padding(.bottom, tabHeight)
                    TabBar().frame(height: Metrics.tabBar).padding(.bottom, bottomSafe).background(Palette.paper.shadow(.drop(color: .black.opacity(0.06), radius: 1, y: -1)))
                }
                .frame(maxHeight: .infinity, alignment: .bottom)
                .ignoresSafeArea(edges: .bottom)

                TopBar()
            }
        }
        .background(Palette.paper)
        .task { await app.loadFields() }
        .sheet(isPresented: $app.dateOpen) { DateSheet().presentationDetents([.medium, .large]).presentationCornerRadius(Radius.xl) }
        .sheet(isPresented: $app.layersOpen) { LayersSheet().presentationDetents([.medium]).presentationCornerRadius(Radius.xl) }
        .sheet(isPresented: $app.sourcesOpen) { SourcesSheet(bc: app.selectedField?.isBC ?? false).presentationDetents([.large]).presentationCornerRadius(Radius.xl) }
        .fullScreenCover(isPresented: $app.drillOpen) {
            if let s = app.session { DrillDownView(session: s) }
        }
    }
}

enum SheetGeometry {
    static func visibleHeight(_ d: SheetDetent, screen: CGFloat, max: CGFloat) -> CGFloat {
        switch d {
        case .peek: Metrics.peek
        case .half: min(max, (screen * 0.52).rounded())
        case .full: max
        }
    }
}

/// What the sheet shows: the pick list, or the open field's section.
struct SheetContent: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        Group {
            if app.pickerOpen || app.session == nil {
                PickerPanel()
            } else if let s = app.session {
                FieldSheet(session: s)
            }
        }
        .animation(.default, value: app.pickerOpen)
    }
}

/// The open field: a paper header that compresses when scrolled, then the section for the tab.
struct FieldSheet: View {
    let session: FieldSession
    @Environment(AppModel.self) private var app
    @State private var stuck = false
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        VStack(spacing: 0) {
            FieldHeader(field: session.field, stuck: stuck || app.detent == .peek)
                .background(Palette.paper)
                .overlay(alignment: .bottom) { if stuck { Hairline() } }
            if let error = session.blockingError {
                ErrorStateView(error: error) { Task { await session.load(force: true) } }
                Spacer(minLength: 0)
            } else {
                SheetScroll(stuck: $stuck) {
                    switch app.tab {
                    case .now: FieldNowPanel(session: session)
                    case .season: SeasonPanel(session: session)
                    case .year: YearPanel(session: session)
                    case .compare: ComparePanel(session: session)
                    case .print: PrintPanel(session: session)
                    }
                }
                .id(session.field.id + app.tab.rawValue)
                .transition(.opacity)
            }
        }
        .animation(Motion.std(reduce, 0.24), value: stuck)
        .animation(Motion.std(reduce, 0.24), value: app.tab)
    }
}

/// Scroll content that only scrolls at full (below that a drag moves the sheet, as in Google Maps) and reports
/// when content has passed under the header.
struct SheetScroll<Content: View>: View {
    @Binding var stuck: Bool
    @ViewBuilder let content: Content
    @Environment(AppModel.self) private var app

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                GeometryReader { g in
                    Color.clear.preference(key: ScrollTopKey.self, value: g.frame(in: .named("sheet-scroll")).minY)
                }
                .frame(height: 0)
                content
                    .padding(.horizontal, Metrics.gutter)
                    .padding(.bottom, 32)
            }
        }
        .coordinateSpace(name: "sheet-scroll")
        .scrollDisabled(app.detent != .full)
        .onPreferenceChange(ScrollTopKey.self) { y in
            let s = y < -8
            if s != stuck { stuck = s }
        }
        .onChange(of: app.detent) { _, d in if d != .full { stuck = false } }
    }
}

struct ScrollTopKey: PreferenceKey {
    static let defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = nextValue() }
}
