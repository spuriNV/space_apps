import SwiftUI
import UIKit

/// The one-page summary for the adviser, laid out for US Letter (612 x 792 pt) and rendered to PDF.
/// Fixed sizes, not Dynamic Type: it is a printed page. Light colours only.
struct SummaryPage: View {
    static let size = CGSize(width: 612, height: 792)
    let content: SummaryContent
    let thumbnail: UIImage?

    private let ink = Color(hex: 0x191C16)
    private let muted = Color(hex: 0x5A5E54)
    private let green = Color(hex: 0x2F5D34)
    private let brown = Color(hex: 0x8A5A00)

    private func slab(_ size: CGFloat) -> Font { .custom(FontName.slabSemibold, fixedSize: size) }
    private func body(_ size: CGFloat) -> Font { .custom(FontName.franklin, fixedSize: size) }
    private func strong(_ size: CGFloat) -> Font { .custom(FontName.franklinSemibold, fixedSize: size) }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("CropLytics").font(slab(15)).foregroundStyle(.white)
                Spacer()
                Text("Field summary for your adviser · \(GrowerDate.long(content.date))").font(body(9)).foregroundStyle(.white.opacity(0.92))
            }
            .padding(.horizontal, 36).padding(.vertical, 9)
            .background(green)

            VStack(alignment: .leading, spacing: 11) {
                HStack(alignment: .top, spacing: 14) {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(content.fieldName).font(slab(21)).foregroundStyle(ink)
                        Text(content.subtitle).font(body(10.5)).foregroundStyle(ink)
                        Text(content.record).font(body(9)).foregroundStyle(muted)
                        if let n = content.stateFieldNumber {
                            Text("State field no. \(n)").font(body(8)).foregroundStyle(muted)
                        }
                    }
                    Spacer(minLength: 0)
                    if let thumbnail {
                        Image(uiImage: thumbnail).resizable().scaledToFill().frame(width: 104, height: 70).clipped()
                            .overlay(Rectangle().strokeBorder(ink.opacity(0.3), lineWidth: 0.5))
                    }
                }
                rule
                section("This season on the field", content.now)
                rule
                section("What's likely this winter and next season", content.season)
                rule
                comparison
                rule
                VStack(alignment: .leading, spacing: 3) {
                    Text("Check locally before deciding").font(slab(12.5)).foregroundStyle(ink)
                    ForEach(content.checkLocally, id: \.self) { item in
                        Text("• " + item).font(body(8.8)).foregroundStyle(ink).fixedSize(horizontal: false, vertical: true)
                    }
                }
                Spacer(minLength: 0)
                Text("Sources: NASA HLS (Landsat and Sentinel-2), GPM IMERG, GRACE-FO, SMAP, POWER and NASADEM; USDA Cropland Data Layer and soil survey; NOAA Climate Prediction Center; CDEC; Reclamation; US Drought Monitor; OpenET. Outlooks are not forecasts. Rotation numbers are model estimates with likely ranges. CropLytics supports, never replaces, your adviser.")
                    .font(body(7.5)).foregroundStyle(muted).fixedSize(horizontal: false, vertical: true)
            }
            .padding(.horizontal, 36).padding(.top, 16).padding(.bottom, 26)
        }
        .frame(width: Self.size.width, height: Self.size.height, alignment: .top)
        .background(Color(hex: 0xFFFFFF))
    }

    private var rule: some View { Rectangle().fill(ink.opacity(0.25)).frame(height: 0.6) }

    private func section(_ title: String, _ answers: [Answer]) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title).font(slab(12.5)).foregroundStyle(ink)
            ForEach(answers) { a in
                VStack(alignment: .leading, spacing: 1) {
                    HStack(alignment: .firstTextBaseline, spacing: 4) {
                        Text(a.question).font(body(8.5)).foregroundStyle(muted)
                    }
                    Text(a.headline).font(strong(9.8)).foregroundStyle(a.tone == .warn ? brown : ink)
                    Text(a.detail).font(body(8.6)).foregroundStyle(ink).fixedSize(horizontal: false, vertical: true).lineLimit(3)
                }
            }
        }
    }

    @ViewBuilder private var comparison: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("The option to talk about").font(slab(12.5)).foregroundStyle(ink)
            if let today = content.today, let alt = content.alternative {
                Text("Today: \(today.name.lowercased()), about \(Units.oneDecimal(today.water?.value ?? 0)) acre-ft/acre a year. Option: \(alt.option.name.lowercased()), about \(Units.oneDecimal(alt.option.water?.value ?? 0)) (\(alt.option.fit.text.lowercased())). Water limit \(Units.oneDecimal(content.limit.value))\(content.limit.isExample ? " (example, not the grower's own)" : "").")
                    .font(body(9)).foregroundStyle(ink).fixedSize(horizontal: false, vertical: true)
                HStack(alignment: .top, spacing: 18) {
                    trade("Gains", alt.gains, green)
                    trade("Gives up", alt.losses, brown)
                }
            } else {
                Text("Rotation scores weren't available when this page was made.").font(body(9)).foregroundStyle(muted)
            }
        }
    }

    private func trade(_ title: String, _ lines: [TradeLine], _ color: Color) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title).font(strong(9.5)).foregroundStyle(color)
            if lines.isEmpty { Text("Nothing clear").font(body(8.6)).foregroundStyle(muted) }
            ForEach(lines) { l in
                Text("\(l.title): \(l.delta).").font(body(8.6)).foregroundStyle(ink).fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
