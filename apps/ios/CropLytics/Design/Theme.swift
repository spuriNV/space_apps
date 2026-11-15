import SwiftUI
import UIKit

// The "Extension bulletin" look from .claude/skills/fieldshift-visual-design:
// paper, black ink, one spot green; brown only for "example numbers" and "over the limit"; red for problems.
// Components read these tokens only. Data colours (bare / partial / covered / water) are fixed and never reused for chrome.

extension UIColor {
    convenience init(hex: UInt32, alpha: CGFloat = 1) {
        self.init(
            red: CGFloat((hex >> 16) & 0xFF) / 255,
            green: CGFloat((hex >> 8) & 0xFF) / 255,
            blue: CGFloat(hex & 0xFF) / 255,
            alpha: alpha
        )
    }

    static func dynamic(light: UInt32, dark: UInt32, lightAlpha: CGFloat = 1, darkAlpha: CGFloat = 1) -> UIColor {
        UIColor { traits in
            traits.userInterfaceStyle == .dark ? UIColor(hex: dark, alpha: darkAlpha) : UIColor(hex: light, alpha: lightAlpha)
        }
    }
}

extension Color {
    init(hex: UInt32) { self.init(uiColor: UIColor(hex: hex)) }
}

enum Palette {
    /// Paper: the page background.
    static let paper = Color(uiColor: .dynamic(light: 0xF7F6F0, dark: 0x141612))
    /// A slightly darker paper for grouped blocks (the summary card, the limit editor).
    static let panel2 = Color(uiColor: .dynamic(light: 0xEBEAE0, dark: 0x1F221C))
    /// Black ink: body text, >= 7:1 on paper in both modes.
    static let text = Color(uiColor: .dynamic(light: 0x191C16, dark: 0xECEBE3))
    static let text2 = Color(uiColor: .dynamic(light: 0x363A31, dark: 0xD2D2C8))
    /// Muted ink for labels and source lines, >= 4.5:1 on paper.
    static let muted = Color(uiColor: .dynamic(light: 0x5A5E54, dark: 0xA6A99E))
    /// Hairline rules.
    static let line = Color(uiColor: .dynamic(light: 0x191C16, dark: 0xECEBE3, lightAlpha: 0.22, darkAlpha: 0.24))
    static let lineSoft = Color(uiColor: .dynamic(light: 0x191C16, dark: 0xECEBE3, lightAlpha: 0.11, darkAlpha: 0.13))
    /// The one spot green: header band, primary action, links, "good".
    static let accent = Color(uiColor: .dynamic(light: 0x2F5D34, dark: 0x8FC495))
    static let accentInk = Color(uiColor: .dynamic(light: 0xFFFFFF, dark: 0x0F1A10))
    static let accentSoft = Color(uiColor: .dynamic(light: 0x2F5D34, dark: 0x8FC495, lightAlpha: 0.12, darkAlpha: 0.16))
    /// Brown: example numbers and "over the limit" only.
    static let warn = Color(uiColor: .dynamic(light: 0x8A5A00, dark: 0xE2B45E))
    /// Red: problems only.
    static let bad = Color(uiColor: .dynamic(light: 0xA12A1C, dark: 0xF2907F))
    static let mark = text
    /// Field selection on imagery: yellow outline with a dark shadow.
    static let fieldOutline = Color(hex: 0xFFD166)
}

/// Fixed data colours (frontend/app/src/lib.ts). Same in light and dark so a strip means the same thing everywhere.
enum DataColor {
    static let bare = Color(hex: 0xA8703F)
    static let partial = Color(hex: 0xB7D77A)
    static let covered = Color(hex: 0x2F9E4B)
    static let water = Color(hex: 0x3D97E8)
    static let noView = Color(hex: 0x9A9C94)
    static let soil = Color(hex: 0x8A5A2B)
    static let groundwater = Color(hex: 0x2F6FB5)

    static func crop(_ name: String) -> Color {
        if name.hasPrefix("Rice") { return Color(hex: 0x3D7FC4) }
        if name == "Left fallow" { return Color(hex: 0xB08A5A) }
        if name.hasPrefix("Alfalfa") { return Color(hex: 0x4F8F3A) }
        if name.hasPrefix("Corn") { return Color(hex: 0xD4B23C) }
        if name.hasPrefix("Wheat") { return Color(hex: 0xC79A3A) }
        return Color(hex: 0x8A8A80)
    }
}

enum Metrics {
    static let radius: CGFloat = 4
    static let gutter: CGFloat = 16
}
