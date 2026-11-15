import Foundation
import Observation

/// The five sections, as bottom tabs (web: Field now, Coming season, This field's year, Compare, Print for your adviser).
enum AppTab: String, Hashable, CaseIterable, Sendable {
    case now, season, year, compare, print

    var title: String {
        switch self {
        case .now: "Now"
        case .season: "Season"
        case .year: "Year"
        case .compare: "Compare"
        case .print: "Print"
        }
    }

    var longTitle: String {
        switch self {
        case .now: "Field now"
        case .season: "Coming season"
        case .year: "This field's year"
        case .compare: "Compare"
        case .print: "Print for your adviser"
        }
    }
}

/// Sheet snap points (redesign §5.2): peek 128pt, half 52% of the screen, full.
enum SheetDetent: Int, Comparable, CaseIterable, Sendable {
    case peek, half, full
    static func < (a: SheetDetent, b: SheetDetent) -> Bool { a.rawValue < b.rawValue }
}

/// Map layers the grower can switch on (web LayersDrawer).
enum MapLayer: String, CaseIterable, Hashable, Sendable {
    case outlines, smap, grace, imerg, reserves
    var title: String {
        switch self {
        case .outlines: "Every field's outline"
        case .smap: "Soil moisture square (NASA SMAP)"
        case .grace: "Groundwater square (NASA GRACE-FO)"
        case .imerg: "Rain square (NASA GPM IMERG)"
        case .reserves: "Reserve boundaries (BC, context only)"
        }
    }
    var tellsYou: String {
        switch self {
        case .outlines: "All the fields the app knows, outlined on the imagery."
        case .smap: "One soil-moisture reading covers this 6-mile square."
        case .grace: "One groundwater reading covers this 17-mile square; the satellites sense about 190 miles."
        case .imerg: "One rain reading covers this 6-mile square."
        case .reserves: "Indian reserve outlines near the field, from the BC Data Catalogue. No reserve land is analysed."
        }
    }
    /// Side of the footprint square in degrees.
    var footprintDegrees: Double? {
        switch self {
        case .smap: 0.09
        case .grace: 0.25
        case .imerg: 0.1
        default: nil
        }
    }
}

/// App-wide state: the fields, the open field and its data, the tab, the viewing date, the sheet and the map.
@MainActor
@Observable
final class AppModel {
    var tab: AppTab
    private(set) var fields: LoadState<[FieldLocation]> = .idle
    private(set) var selectedFieldID: String?
    private(set) var session: FieldSession?

    /// The viewing date; `today` unless the grower picked another.
    var t: TimePoint
    let today: TimePoint
    var playing = false
    var showEarlier = false
    var detent: SheetDetent = .half
    /// Picker shown in the sheet (no field yet, or the grower tapped the field switcher).
    var pickerOpen = true
    /// The app-wide "More detail" switch (adviser detail), remembered on the phone.
    var detailOn: Bool { didSet { defaults.set(detailOn, forKey: Self.detailKey) } }
    var layers: Set<MapLayer> = [.outlines, .smap]
    var drillOpen = false
    var layersOpen = false
    var dateOpen = false
    var sourcesOpen = false
    /// Bumped to ask the map to fly home or to the field.
    private(set) var cameraRequest = 0
    private(set) var homeRequested = false

    private let repository: any FieldRepository
    private let defaults: UserDefaults
    private let limits: WaterLimitStore?
    private static let lastFieldKey = "lastFieldID"
    private static let detailKey = "detailOn"
    private var playTask: Task<Void, Never>?

    init(repository: any FieldRepository, defaults: UserDefaults = .standard, today: Date = .now, limits: WaterLimitStore? = nil,
         initialTab: AppTab? = nil, initialField: String? = nil) {
        self.repository = repository
        self.defaults = defaults
        self.limits = limits
        self.today = TimePoint(date: today)
        self.t = TimePoint(date: today)
        tab = initialTab ?? .now
        detailOn = defaults.bool(forKey: Self.detailKey)
        if let id = initialField ?? defaults.string(forKey: Self.lastFieldKey) {
            selectedFieldID = id
            pickerOpen = false
        }
    }

    var selectedField: FieldLocation? { session?.field }
    var isToday: Bool { t == today }

    func loadFields() async {
        if fields.value == nil { fields = .loading }
        await consume(repository.locations()) { state in
            self.fields = state
            if let list = state.value {
                self.limits?.registerExamples(list)
                if let id = self.selectedFieldID, let f = list.first(where: { $0.id == id }) {
                    if self.session?.field.id == id { self.session?.update(field: f) } else { self.openSession(f) }
                }
            }
        }
    }

    /// Opens a field: its data loads once and every tab shares it; the map flies there.
    func open(_ fieldID: String, tab: AppTab? = nil) {
        guard let f = fields.value?.first(where: { $0.id == fieldID }) else { return }
        selectedFieldID = fieldID
        defaults.set(fieldID, forKey: Self.lastFieldKey)
        if session?.field.id != fieldID { openSession(f) }
        if let tab { self.tab = tab }
        pickerOpen = false
        detent = .half
        drillOpen = false
        homeRequested = false
        cameraRequest += 1
    }

    private func openSession(_ f: FieldLocation) {
        let s = FieldSession(field: f, repository: repository)
        session = s
        Task { await s.load() }
    }

    /// Back to the pick list (the field stays open underneath, as on the web).
    func showPicker() {
        pickerOpen = true
        detent = .half
    }

    /// Close the field: whole state on the map, the pick list in the sheet.
    func goHome() {
        stopReplay()
        selectedFieldID = nil
        session = nil
        defaults.removeObject(forKey: Self.lastFieldKey)
        pickerOpen = true
        drillOpen = false
        homeRequested = true
        cameraRequest += 1
    }

    func select(tab: AppTab) {
        guard selectedField != nil else { pickerOpen = true; return }
        pickerOpen = false
        self.tab = tab
        if detent == .peek { detent = .half }
    }

    func flyToField() { homeRequested = false; cameraRequest += 1 }

    // MARK: Date and replay

    func setDate(_ new: TimePoint) {
        t = min(new, today)
    }

    func backToToday() { stopReplay(); t = today }

    /// Replay the seasons on the map: one 10-day step every 0.22 s from the first shown year to today.
    func toggleReplay() {
        if playing { stopReplay(); return }
        playing = true
        let start = TimePoint(year: showEarlier ? TimePoint.firstYear : today.year - 3, dekad: 0)
        if t >= today { t = start }
        playTask = Task { [weak self] in
            while let self, self.playing, !Task.isCancelled {
                try? await Task.sleep(for: .milliseconds(220))
                guard self.playing else { break }
                self.t = self.t >= self.today ? start : self.t.advanced(by: 1)
            }
        }
    }

    func stopReplay() {
        playing = false
        playTask?.cancel()
        playTask = nil
    }
}
