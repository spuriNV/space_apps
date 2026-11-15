import SwiftUI
import UIKit

/// Zilla Slab for headings, place names and answers; Libre Franklin for UI, data and source lines.
/// Sizes follow the redesign scale (§3.6): 28 / 22 / 20 / 16 / 14.5 / 13, each relative to a text style so Dynamic Type scales it.
enum FontName {
    static let slabMedium = "ZillaSlab-Medium"
    static let slabSemibold = "ZillaSlab-SemiBold"
    static let franklin = "LibreFranklin-Regular"
    static let franklinSemibold = "LibreFranklin-SemiBold"
    static let franklinBold = "LibreFranklin-Bold"
}

extension Font {
    /// Field name (28; the phone sheet uses `clTitlePhone`).
    static let clTitle = Font.custom(FontName.slabSemibold, size: 28, relativeTo: .title)
    static let clTitlePhone = Font.custom(FontName.slabSemibold, size: 22, relativeTo: .title2)
    /// Section headings.
    static let clHeading = Font.custom(FontName.slabSemibold, size: 22, relativeTo: .title2)
    /// Answer sentences, meter values, row titles.
    static let clAnswer = Font.custom(FontName.slabSemibold, size: 20, relativeTo: .title3)
    static let clRowTitle = Font.custom(FontName.slabSemibold, size: 18, relativeTo: .headline)
    static let clBody = Font.custom(FontName.franklin, size: 16, relativeTo: .body)
    static let clBodyStrong = Font.custom(FontName.franklinSemibold, size: 16, relativeTo: .body)
    static let clBodyBold = Font.custom(FontName.franklinBold, size: 16, relativeTo: .body)
    /// Questions, chips, notes (14.5).
    static let clLabel = Font.custom(FontName.franklinSemibold, size: 14.5, relativeTo: .subheadline)
    static let clSecondary = Font.custom(FontName.franklin, size: 14.5, relativeTo: .subheadline)
    /// Source lines, meter labels, ids (13).
    static let clCite = Font.custom(FontName.franklin, size: 13, relativeTo: .footnote)
    static let clCiteStrong = Font.custom(FontName.franklinSemibold, size: 13, relativeTo: .footnote)
    static let clNumber = Font.custom(FontName.slabSemibold, size: 20, relativeTo: .title3).monospacedDigit()
    static let clSmallNumber = Font.custom(FontName.franklin, size: 13, relativeTo: .footnote).monospacedDigit()
    static let clWordmark = Font.custom(FontName.slabSemibold, size: 21, relativeTo: .title3)
}

enum AppAppearance {
    /// Navigation bars (pushed screens such as "All options") in the heading face, scaled with Dynamic Type.
    @MainActor static func apply() {
        let nav = UINavigationBarAppearance()
        nav.configureWithDefaultBackground()
        nav.backgroundColor = UIColor.dynamic(light: 0xF7F6F0, dark: 0x171A15)
        nav.shadowColor = UIColor.dynamic(light: 0x191C16, dark: 0xECEBE3, lightAlpha: 0.14, darkAlpha: 0.14)
        let ink = UIColor.dynamic(light: 0x191C16, dark: 0xECEBE3)
        if let f = UIFont(name: FontName.slabSemibold, size: 19) {
            nav.titleTextAttributes = [.font: UIFontMetrics(forTextStyle: .headline).scaledFont(for: f), .foregroundColor: ink]
        }
        UINavigationBar.appearance().standardAppearance = nav
        UINavigationBar.appearance().compactAppearance = nav
        UINavigationBar.appearance().scrollEdgeAppearance = nav
    }
}

/// Motion (§6): standard easing, spring for the sheet, all collapsed to near-instant with Reduce Motion.
enum Motion {
    static func std(_ reduce: Bool, _ duration: Double = 0.18) -> Animation {
        reduce ? .linear(duration: 0.001) : .timingCurve(0.2, 0, 0, 1, duration: duration)
    }
    static func sheet(_ reduce: Bool) -> Animation {
        reduce ? .linear(duration: 0.001) : .spring(response: 0.36, dampingFraction: 0.86)
    }
    static func enter(_ reduce: Bool) -> Animation {
        reduce ? .linear(duration: 0.001) : .timingCurve(0.05, 0.7, 0.1, 1, duration: 0.32)
    }
}
