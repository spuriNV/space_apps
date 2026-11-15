import SwiftUI
import Charts

/// One season as 36 ten-day steps: bare, thin, green, water; no clear view is hatched grey.
/// Drawn with Canvas so "no clear view" can be hatched, as on the web timeline.
struct SeasonStripView: View {
    let classes: [CoverClass]
    var marker: Int?
    var height: CGFloat = 16

    var body: some View {
        Canvas { ctx, size in
            let n = max(classes.count, 1)
            let w = size.width / CGFloat(n)
            for (i, c) in classes.enumerated() {
                let rect = CGRect(x: CGFloat(i) * w, y: 0, width: w + 0.5, height: size.height)
                if c == .noView {
                    ctx.fill(Path(rect), with: .color(DataColor.noView.opacity(0.25)))
                    var hatch = Path()
                    var x = rect.minX - size.height
                    while x < rect.maxX {
                        hatch.move(to: CGPoint(x: x, y: size.height))
                        hatch.addLine(to: CGPoint(x: x + size.height, y: 0))
                        x += 4
                    }
                    ctx.drawLayer { layer in
                        layer.clip(to: Path(rect)) // keep the hatch inside the cell
                        layer.stroke(hatch, with: .color(DataColor.noView), lineWidth: 1)
                    }
                } else {
                    ctx.fill(Path(rect), with: .color(Self.color(c)))
                }
            }
            if let m = marker, m < n {
                let x = (CGFloat(m) + 0.5) * w
                var line = Path()
                line.move(to: CGPoint(x: x, y: -2))
                line.addLine(to: CGPoint(x: x, y: size.height + 2))
                ctx.stroke(line, with: .color(Palette.mark), lineWidth: 2)
            }
        }
        .frame(height: height)
        .overlay(Rectangle().strokeBorder(Palette.lineSoft))
        .accessibilityElement()
        .accessibilityLabel(Self.describe(classes))
    }

    static func color(_ c: CoverClass) -> Color {
        switch c {
        case .bare: DataColor.bare
        case .partial: DataColor.partial
        case .covered: DataColor.covered
        case .water: DataColor.water
        case .noView: DataColor.noView
        }
    }

    /// VoiceOver: "Green 12 steps, bare 6, ..." in days.
    static func describe(_ classes: [CoverClass]) -> String {
        let counted = CoverClass.allCases.compactMap { c -> String? in
            let n = classes.filter { $0 == c }.count
            return n == 0 ? nil : "\(c.label) about \(n * 10) days"
        }
        return "Season strip: " + counted.joined(separator: ", ")
    }
}

/// Month labels under a 36-step strip.
struct StripMonths: View {
    var body: some View {
        HStack {
            ForEach(["Jan", "Apr", "Jul", "Oct"], id: \.self) { m in
                Text(m).font(.clCite).foregroundStyle(Palette.muted).frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .accessibilityHidden(true)
    }
}

/// Key for the strip colours.
struct StripKey: View {
    var classes: [CoverClass] = [.covered, .partial, .bare, .water, .noView]
    var body: some View {
        FlowLayout(spacing: 10) {
            ForEach(classes, id: \.self) { c in
                HStack(spacing: 4) {
                    RoundedRectangle(cornerRadius: 1).fill(SeasonStripView.color(c).opacity(c == .noView ? 0.5 : 1)).frame(width: 10, height: 10)
                    Text(c.label).font(.clCite).foregroundStyle(Palette.muted)
                }
            }
        }
        .accessibilityHidden(true)
    }
}

/// One reading as a bar with a reference tick (normal, limit, full canopy). Swift Charts.
struct MeterView: View {
    let meter: Meter

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(meter.label).font(.clSecondary).foregroundStyle(Palette.muted)
            Text(meter.valueText).font(.clNumber).foregroundStyle(meter.warn ? Palette.warn : Palette.text)
            Chart {
                BarMark(xStart: .value("Start", 0), xEnd: .value("Scale", meter.scaleMax), y: .value("Row", "track"), height: 8)
                    .foregroundStyle(Palette.lineSoft)
                BarMark(xStart: .value("Start", 0), xEnd: .value(meter.label, min(meter.value, meter.scaleMax)), y: .value("Row", "track"), height: 8)
                    .foregroundStyle(meter.warn ? Palette.warn : Palette.accent)
                if let ref = meter.reference {
                    RuleMark(x: .value(meter.referenceLabel, min(ref, meter.scaleMax)), yStart: 0, yEnd: 18)
                        .foregroundStyle(Palette.mark)
                        .lineStyle(StrokeStyle(lineWidth: 2))
                }
            }
            .chartXScale(domain: 0...max(meter.scaleMax, 0.01))
            .chartXAxis(.hidden)
            .chartYAxis(.hidden)
            .chartLegend(.hidden)
            .frame(height: 18)
            Text(meter.note + (meter.reference != nil ? " · line = \(meter.referenceLabel)" : ""))
                .font(.clCite)
                .foregroundStyle(Palette.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(meter.accessibilityText)
    }
}

/// Soil moisture and groundwater as dots on one 0-100 percentile track; 50 is normal.
struct PercentileTrack: View {
    let soil: Double?
    let groundwater: Double?
    let note: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Soil and groundwater").font(.clSecondary).foregroundStyle(Palette.muted)
            Chart {
                RectangleMark(xStart: .value("Low", 0), xEnd: .value("High", 100), y: .value("Row", "t"), height: 6)
                    .foregroundStyle(Palette.lineSoft)
                RectangleMark(xStart: .value("Usual low", 33), xEnd: .value("Usual high", 67), y: .value("Row", "t"), height: 6)
                    .foregroundStyle(Palette.line)
                RuleMark(x: .value("Normal", 50)).foregroundStyle(Palette.muted).lineStyle(StrokeStyle(lineWidth: 1, dash: [2, 2]))
                if let soil {
                    PointMark(x: .value("Soil", soil), y: .value("Row", "t"))
                        .symbol(.circle).symbolSize(110).foregroundStyle(DataColor.soil)
                }
                if let groundwater {
                    PointMark(x: .value("Groundwater", groundwater), y: .value("Row", "t"))
                        .symbol(.diamond).symbolSize(110).foregroundStyle(DataColor.groundwater)
                }
            }
            .chartXScale(domain: 0...100)
            .chartXAxis {
                AxisMarks(values: [0, 50, 100]) { v in
                    AxisValueLabel {
                        if let n = v.as(Int.self) {
                            Text(n == 0 ? "driest" : n == 100 ? "wettest" : "normal").font(.clCite)
                        }
                    }
                }
            }
            .chartYAxis(.hidden)
            .frame(height: 40)
            HStack(spacing: 12) {
                keyItem(shape: AnyShape(Circle()), color: DataColor.soil, text: "Soil \(soil.map { Units.ordinal(Int($0.rounded())) } ?? "–")")
                keyItem(shape: AnyShape(Diamond()), color: DataColor.groundwater, text: "Groundwater \(groundwater.map { Units.ordinal(Int($0.rounded())) } ?? "–")")
            }
            Text(note).font(.clCite).foregroundStyle(Palette.muted).fixedSize(horizontal: false, vertical: true)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Soil moisture \(soil.map { Units.ordinal(Int($0.rounded())) + " percentile" } ?? "not available"), groundwater \(groundwater.map { Units.ordinal(Int($0.rounded())) + " percentile" } ?? "not available"). \(note)")
    }

    private func keyItem(shape: AnyShape, color: Color, text: String) -> some View {
        HStack(spacing: 4) {
            shape.fill(color).frame(width: 9, height: 9)
            Text(text).font(.clCite).foregroundStyle(Palette.text2)
        }
    }
}

struct Diamond: Shape {
    func path(in r: CGRect) -> Path {
        Path { p in
            p.move(to: CGPoint(x: r.midX, y: r.minY)); p.addLine(to: CGPoint(x: r.maxX, y: r.midY))
            p.addLine(to: CGPoint(x: r.midX, y: r.maxY)); p.addLine(to: CGPoint(x: r.minX, y: r.midY)); p.closeSubpath()
        }
    }
}

/// Twelve months of a rotation: what covers the field each month.
struct MonthStrip: View {
    let months: [CoverClass]
    var body: some View {
        HStack(spacing: 2) {
            ForEach(Array(months.enumerated()), id: \.offset) { _, c in
                Rectangle().fill(SeasonStripView.color(c)).frame(height: 10)
            }
        }
        .accessibilityElement()
        .accessibilityLabel(SeasonStripView.describe(months).replacingOccurrences(of: "about ", with: "").replacingOccurrences(of: "0 days", with: " months"))
    }
}

/// A simple wrapping row layout.
struct FlowLayout: Layout {
    var spacing: CGFloat = 8
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? .infinity
        var x: CGFloat = 0, y: CGFloat = 0, row: CGFloat = 0, maxX: CGFloat = 0
        for s in subviews {
            let size = s.sizeThatFits(.unspecified)
            if x + size.width > width, x > 0 { x = 0; y += row + spacing / 2; row = 0 }
            x += size.width + spacing; row = max(row, size.height); maxX = max(maxX, x)
        }
        return CGSize(width: min(maxX, width), height: y + row)
    }
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, row: CGFloat = 0
        for s in subviews {
            let size = s.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX, x > bounds.minX { x = bounds.minX; y += row + spacing / 2; row = 0 }
            s.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing; row = max(row, size.height)
        }
    }
}
