import SwiftUI

@main
struct CropLyticsApp: App {
    @State private var environment: AppEnvironment
    @State private var model: AppModel

    init() {
        let args = ProcessInfo.processInfo.arguments
        let uiTesting = args.contains("-ui-testing")
        let env: AppEnvironment = uiTesting ? .fixtures(wakeDelay: .milliseconds(args.contains("-slow-server") ? 1500 : 0)) : .live()
        // Launch arguments for demos and screenshots: -initialField car_colusa_rice -initialTab compare
        let tab = Self.value(after: "-initialTab", in: args).flatMap(AppTab.init(rawValue:))
        let field = Self.value(after: "-initialField", in: args)
        let defaults = uiTesting ? UserDefaults(suiteName: "CropLyticsFixtures")! : .standard
        if uiTesting { defaults.removeObject(forKey: "lastFieldID") }
        _environment = State(initialValue: env)
        _model = State(initialValue: AppModel(repository: env.repository, defaults: defaults, initialTab: tab, initialField: field))
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
