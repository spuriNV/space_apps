import SwiftUI
import UIKit

// Tokens from docs/ui-redesign-spec.md §3 (mock/tokens.css), light and dark.
// Paper, ink and one spot green; green marks the one primary action, links and focus. Selected = a pale tonal fill.
// Components read these tokens only. Data colours (bare / partial / covered / water, soil, crops) never change with the theme.

extension UIColor {
    convenience init(hex: UInt32, alpha: CGFloat = 1) {
        self.init(red: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255, blue: CGFloat(hex & 0xFF) / 255, alpha: alpha)
    }

    static func dynamic(light: UInt32, dark: UInt32, lightAlpha: CGFloat = 1, darkAlpha: CGFloat = 1) -> UIColor {
        UIColor { $0.userInterfaceStyle == .dark ? UIColor(hex: dark, alpha: darkAlpha) : UIColor(hex: light, alpha: lightAlpha) }
    }
}

extension Color {
    init(hex: UInt32) { self.init(uiColor: UIColor(hex: hex)) }
    fileprivate static func token(_ light: UInt32, _ dark: UInt32, _ la: CGFloat = 1, _ da: CGFloat = 1) -> Color {
        Color(uiColor: .dynamic(light: light, dark: dark, lightAlpha: la, darkAlpha: da))
    }
}

enum Palette {
    /// Paper: panel, sheet, top bar.
    static let paper = Color.token(0xF7F6F0, 0x171A15)
    /// Sunken: search field, disclosure row, segmented track.
    static let panel2 = Color.token(0xEFEEE7, 0x20241D)
    /// Cards on paper (the glance card), the segmented thumb.
    static let raised = Color.token(0xFFFFFF, 0x23281F)
    static let text = Color.token(0x191C16, 0xECEBE3)
    static let text2 = Color.token(0x363A31, 0xC9CBC0)
    static let muted = Color.token(0x5A5E54, 0xA3A69A)
    /// Row dividers.
    static let line = Color.token(0x191C16, 0xECEBE3, 0.14, 0.14)
    /// Card edges.
    static let lineSoft = Color.token(0x191C16, 0xECEBE3, 0.08, 0.08)
    /// Chip and input edges that must be seen (3.4:1).
    static let outline = Color.token(0x84877D, 0x6C7066)
    static let accent = Color.token(0x2F5D34, 0x9FCB9B)
    static let accentPressed = Color.token(0x22442A, 0x8DBD89)
    static let accentInk = Color.token(0xFFFFFF, 0x10260F)
    /// Selected state: chips, rows, tab pill, tonal buttons.
    static let accentContainer = Color.token(0xE3ECDD, 0x2B3F2B)
    static let accentContainerHover = Color.token(0xD7E4D0, 0x344B34)
    static let onAccentContainer = Color.token(0x1D3A21, 0xCFE6C9)
    static let accentOutline = Color.token(0x5F8A5C, 0x7FAE7B)
    static let warn = Color.token(0x8A5A00, 0xE0B04A)
    static let warnContainer = Color.token(0xF4EAD6, 0x3A2E14)
    static let onWarnContainer = Color.token(0x6B4600, 0xF1D38F)
    static let bad = Color.token(0xA12A1C, 0xF08A7A)
    static let mark = text
    /// Ink state layers: hover 5%, pressed 10%, strong 14% (dark: paper ink 6/12/16%).
    static let statePressed = Color.token(0x191C16, 0xECEBE3, 0.10, 0.12)
    static let stateHover = Color.token(0x191C16, 0xECEBE3, 0.05, 0.06)
    static let stateStrong = Color.token(0x191C16, 0xECEBE3, 0.14, 0.16)
    /// Field selection on imagery: yellow outline with a dark shadow.
    static let fieldOutline = Color(hex: 0xFFD166)
    /// The 3px spot-green band under the top bar: the only header band.
    static let band = Color(hex: 0x2F5D34)
}

/// Fixed data colours (frontend/app/src/lib.ts). Same in light and dark.
enum DataColor {
    static let bare = Color(hex: 0xA8703F)
    static let partial = Color(hex: 0xB7D77A)
    static let covered = Color(hex: 0x2F9E4B)
    static let water = Color(hex: 0x3D97E8)
    static let noView = Color(hex: 0x9A9C94)
    static let soil = Color(hex: 0x8A5A2B)
    static let groundwater = Color(hex: 0x2F6FB5)
    static let sand = Color(hex: 0xD9B46A)
    static let silt = Color(hex: 0xE9E3D3)
    static let clay = Color(hex: 0x7A4A2B)

    static func crop(_ name: String) -> Color {
        if name.hasPrefix("Rice") { return Color(hex: 0x3D7FC4) }
        if name == "Left fallow" { return Color(hex: 0xB08A5A) }
        if name.hasPrefix("Alfalfa") { return Color(hex: 0x4F8F3A) }
        if name.hasPrefix("Corn") { return Color(hex: 0xD4B23C) }
        if name.hasPrefix("Wheat") { return Color(hex: 0xC79A3A) }
        if name.lowercased().contains("hay") || name.lowercased().contains("pasture") || name.lowercased().contains("forage") { return Color(hex: 0x6E9F4A) }
        return Color(hex: 0x8A8A80)
    }
}

/// Shape scale (§3.3).
enum Radius {
    static let xs: CGFloat = 4
    static let sm: CGFloat = 8
    static let md: CGFloat = 12
    static let lg: CGFloat = 16
    static let xl: CGFloat = 20
}

enum Metrics {
    static let radius: CGFloat = Radius.md
    static let gutter: CGFloat = 16
    static let sectionGap: CGFloat = 24
    static let peek: CGFloat = 128
    static let tabBar: CGFloat = 64
    static let topBar: CGFloat = 56
}

extension View {
    /// e1: cards and the segmented thumb.
    func elevation1() -> some View { shadow(color: .black.opacity(0.08), radius: 2, y: 1) }
    /// e2: a surface floating over the map.
    func elevation2() -> some View { shadow(color: .black.opacity(0.18), radius: 16, y: 8) }
    /// e3: menus and popovers.
    func elevation3() -> some View { shadow(color: .black.opacity(0.24), radius: 24, y: 12) }
    /// Sheet: the shadow points up.
    func elevationSheet() -> some View { shadow(color: .black.opacity(0.18), radius: 16, y: -6) }
}
