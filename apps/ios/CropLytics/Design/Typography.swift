import SwiftUI
import UIKit

/// Zilla Slab for headings, place names and answers; Libre Franklin for UI, data and source lines.
/// Both are SIL OFL fonts bundled in Resources/Fonts and registered through UIAppFonts in Info.plist.
/// Every size is relative to a text style, so Dynamic Type scales them.
enum FontName {
    static let slabMedium = "ZillaSlab-Medium"
    static let slabSemibold = "ZillaSlab-SemiBold"
    static let franklin = "LibreFranklin-Regular"
    static let franklinSemibold = "LibreFranklin-SemiBold"
    static let franklinBold = "LibreFranklin-Bold"
}

extension Font {
    /// Screen titles and the field name.
    static let clTitle = Font.custom(FontName.slabSemibold, size: 26, relativeTo: .title)
    /// Section headings ("Your field now", "You gain").
    static let clHeading = Font.custom(FontName.slabSemibold, size: 19, relativeTo: .title3)
    /// The plain answer to a question.
    static let clAnswer = Font.custom(FontName.slabMedium, size: 18, relativeTo: .headline)
    /// Body copy.
    static let clBody = Font.custom(FontName.franklin, size: 16, relativeTo: .body)
    static let clBodyStrong = Font.custom(FontName.franklinSemibold, size: 16, relativeTo: .body)
    /// The question above an answer, row labels.
    static let clLabel = Font.custom(FontName.franklinSemibold, size: 14, relativeTo: .subheadline)
    static let clSecondary = Font.custom(FontName.franklin, size: 14, relativeTo: .subheadline)
    /// Source lines.
    static let clCite = Font.custom(FontName.franklin, size: 12.5, relativeTo: .caption)
    static let clCiteItalic = Font.custom(FontName.franklin, size: 12.5, relativeTo: .caption).italic()
    /// Numbers in readings; tabular lining figures so columns line up.
    static let clNumber = Font.custom(FontName.franklinSemibold, size: 17, relativeTo: .body).monospacedDigit()
    static let clSmallNumber = Font.custom(FontName.franklin, size: 13, relativeTo: .footnote).monospacedDigit()
}

enum AppAppearance {
    /// Navigation bar titles in the heading face, scaled with Dynamic Type.
    @MainActor static func apply() {
        let metrics = UIFontMetrics(forTextStyle: .headline)
        let large = UIFontMetrics(forTextStyle: .largeTitle)
        let nav = UINavigationBarAppearance()
        nav.configureWithDefaultBackground()
        nav.backgroundColor = UIColor.dynamic(light: 0xF7F6F0, dark: 0x141612)
        nav.shadowColor = UIColor.dynamic(light: 0x191C16, dark: 0xECEBE3, lightAlpha: 0.22, darkAlpha: 0.24)
        let ink = UIColor.dynamic(light: 0x191C16, dark: 0xECEBE3)
        if let f = UIFont(name: FontName.slabSemibold, size: 18) {
            nav.titleTextAttributes = [.font: metrics.scaledFont(for: f), .foregroundColor: ink]
        }
        if let f = UIFont(name: FontName.slabSemibold, size: 32) {
            nav.largeTitleTextAttributes = [.font: large.scaledFont(for: f), .foregroundColor: ink]
        }
        UINavigationBar.appearance().standardAppearance = nav
        UINavigationBar.appearance().compactAppearance = nav
        UINavigationBar.appearance().scrollEdgeAppearance = nav

        let tab = UITabBarAppearance()
        tab.configureWithDefaultBackground()
        tab.backgroundColor = UIColor.dynamic(light: 0xF7F6F0, dark: 0x141612)
        UITabBar.appearance().standardAppearance = tab
        UITabBar.appearance().scrollEdgeAppearance = tab
    }
}
