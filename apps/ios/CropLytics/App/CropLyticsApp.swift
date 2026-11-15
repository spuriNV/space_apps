import SwiftUI

@main
struct CropLyticsApp: App {
    @State private var environment: AppEnvironment
    @State private var model: AppModel

    init() {
        let args = ProcessInfo.processInfo.arguments
        let uiTesting = args.contains("-ui-testing")
        let env: AppEnvironment = uiTesting ? .fixtures(wakeDelay: .milliseconds(args.contains("-slow-server") ? 1500 : 0)) : .live()
        let defaults = uiTesting ? UserDefaults(suiteName: "CropLyticsFixtures")! : .standard
        if uiTesting { defaults.removeObject(forKey: "lastFieldID"); defaults.removeObject(forKey: "detailOn") }
        // Launch arguments for demos and screenshots:
        //   -initialField car_colusa_rice -initialTab now|season|year|compare|print -detail -sheet peek|half|full -drill -date 2023-03-15
        let model = AppModel(repository: env.repository, defaults: defaults, today: env.today(), limits: env.limits,
                             initialTab: Self.value(after: "-initialTab", in: args).flatMap(AppTab.init(rawValue:)),
                             initialField: Self.value(after: "-initialField", in: args))
        if args.contains("-detail") { model.detailOn = true }
        if let s = Self.value(after: "-sheet", in: args) { model.detent = s == "full" ? .full : s == "peek" ? .peek : .half }
        if args.contains("-picker") { model.pickerOpen = true }
        if args.contains("-drill") { model.drillOpen = true }
        if let d = Self.value(after: "-date", in: args), let t = TimePoint(iso: d) { model.setDate(t) }
        if let l = Self.value(after: "-layers", in: args) { model.layers = Set(l.split(separator: ",").compactMap { MapLayer(rawValue: String($0)) }) }
        _environment = State(initialValue: env)
        _model = State(initialValue: model)
        AppAppearance.apply()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(environment)
                .environment(model)
                .tint(Palette.accent)
        }
    }

    private static func value(after flag: String, in args: [String]) -> String? {
        guard let i = args.firstIndex(of: flag), i + 1 < args.count else { return nil }
        return args[i + 1]
    }
}
