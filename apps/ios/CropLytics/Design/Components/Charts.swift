import SwiftUI
import Charts

/// One season as 36 ten-day steps: bare, thin, green, water; no clear view is hatched grey. Rounded 4pt ends.
/// Canvas so "no clear view" can be hatched, as on the web.
struct SeasonStripView: View {
    let classes: [CoverClass]
    var marker: Int?
    var height: CGFloat = 16
    /// Small ticks on top of the strip (rain days, OPERA water, stress weeks), as 10-day positions.
    var ticks: [StripTick] = []

    var body: some View {
        Canvas { ctx, size in
            let n = max(classes.count, 1)
            let w = size.width / CGFloat(n)
            for (i, c) in classes.enumerated() {
                let rect = CGRect(x: CGFloat(i) * w, y: 0, width: w + 0.5, height: size.height)
                if c == .noView {
                    ctx.fill(Path(rect), with: .color(DataColor.noView.opacity(0.25)))
                    ctx.drawLayer { layer in
                        layer.clip(to: Path(rect))
                        layer.stroke(Hatch(spacing: 4).path(in: rect), with: .color(DataColor.noView), lineWidth: 1)
                    }
                } else {
                    ctx.fill(Path(rect), with: .color(Self.color(c)))
                }
            }
            for t in ticks where t.index < n {
                let x = (CGFloat(t.index) + 0.5) * w
                switch t.kind {
                case .rain(let hit):
                    let dot = CGRect(x: x - 2.5, y: size.height * 0.5 - 2.5, width: 5, height: 5)
                    ctx.fill(Path(ellipseIn: dot), with: .color(hit ? Color(hex: 0x1D3A9E) : .white))
                    ctx.stroke(Path(ellipseIn: dot), with: .color(Color(hex: 0x1D3A9E)), lineWidth: 1)
                case .water:
                    ctx.fill(Path(CGRect(x: CGFloat(t.index) * w, y: 0, width: w, height: 3)), with: .color(DataColor.water))
                case .stress:
                    var p = Path()
                    p.move(to: CGPoint(x: x, y: size.height - 1)); p.addLine(to: CGPoint(x: x - 3, y: size.height - 6)); p.addLine(to: CGPoint(x: x + 3, y: size.height - 6)); p.closeSubpath()
                    ctx.fill(p, with: .color(Palette.bad))
                }
            }
            if let m = marker, m < n {
                let x = (CGFloat(m) + 0.5) * w
                ctx.fill(Path(roundedRect: CGRect(x: x - 1, y: 0, width: 2, height: size.height), cornerRadius: 1), with: .color(Palette.mark))
            }
        }
        .frame(height: height)
        .clipShape(RoundedRectangle(cornerRadius: Radius.xs, style: .continuous))
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

    static func describe(_ classes: [CoverClass]) -> String {
        let counted = CoverClass.allCases.compactMap { c -> String? in
            let n = classes.filter { $0 == c }.count
            return n == 0 ? nil : "\(c.label) about \(n * 10) days"
        }
        return "Season strip: " + counted.joined(separator: ", ")
    }
}

struct StripTick: Sendable, Equatable {
    enum Kind: Sendable, Equatable { case rain(hitBare: Bool), water, stress }
    let index: Int
    let kind: Kind
}

/// A strip that reports which 10-day step was tapped (This field's year: tap a square to move the date).
struct TappableStrip: View {
    let classes: [CoverClass]
    var marker: Int?
    var ticks: [StripTick] = []
    var height: CGFloat = 18
    let onTap: (Int) -> Void

    var body: some View {
        GeometryReader { g in
            SeasonStripView(classes: classes, marker: marker, height: height, ticks: ticks)
                .contentShape(Rectangle())
                .onTapGesture(coordinateSpace: .local) { p in
                    let i = Int(p.x / max(1, g.size.width) * CGFloat(classes.count))
                    onTap(min(max(i, 0), classes.count - 1))
                }
        }
        .frame(height: height)
        .accessibilityAction(named: "Move the date to the latest step") { onTap(classes.count - 1) }
    }
}

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

struct StripKey: View {
    var classes: [CoverClass] = [.covered, .partial, .bare, .water, .noView]
    var body: some View {
        FlowLayout(spacing: 10) {
            ForEach(classes, id: \.self) { c in
                HStack(spacing: 4) {
                    RoundedRectangle(cornerRadius: 2).fill(SeasonStripView.color(c).opacity(c == .noView ? 0.5 : 1)).frame(width: 10, height: 10)
                    Text(c.label).font(.clCite).foregroundStyle(Palette.muted)
                }
            }
        }
        .accessibilityHidden(true)
    }
}

/// One reading: value, a rounded 8pt track with a fill that glides, and a square-topped reference tick (normal, limit, canopy).
struct MeterView: View {
    let meter: Meter
    @Environment(\.accessibilityReduceMotion) private var reduce
    @State private var shown = false

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(meter.label).font(.clCite).foregroundStyle(Palette.muted)
            Text(meter.valueText).font(.clNumber).foregroundStyle(meter.warn ? Palette.warn : Palette.text)
                .lineLimit(1).minimumScaleFactor(0.7)
                .contentTransition(.numericText())
            Chart {
                BarMark(xStart: .value("Start", 0), xEnd: .value("Scale", meter.scaleMax), y: .value("Row", "track"), height: 8)
                    .foregroundStyle(Palette.stateStrong).clipShape(Capsule())
                if meter.value > 0 {
                    BarMark(xStart: .value("Start", 0), xEnd: .value(meter.label, shown ? min(meter.value, meter.scaleMax) : 0), y: .value("Row", "track"), height: 8)
                        .foregroundStyle(meter.warn ? Palette.warn : Palette.accent).clipShape(Capsule())
                }
                if let ref = meter.reference {
                    RuleMark(x: .value(meter.referenceLabel, min(ref, meter.scaleMax)), yStart: 0, yEnd: 16)
                        .foregroundStyle(Palette.mark).lineStyle(StrokeStyle(lineWidth: 2))
                }
            }
            .chartXScale(domain: 0...max(meter.scaleMax, 0.01))
            .chartXAxis(.hidden).chartYAxis(.hidden).chartLegend(.hidden)
            .frame(height: 16)
            Text(meter.note).font(.clCite).foregroundStyle(Palette.muted).fixedSize(horizontal: false, vertical: true)
        }
        .onAppear { withAnimation(Motion.std(reduce, 0.5)) { shown = true } }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(meter.accessibilityText)
    }
}

/// Soil moisture and groundwater as dots on one 0-100 percentile track; 50 is normal.
struct PercentileTrack: View {
    let soil: Double?
    let groundwater: Double?
    var note: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("Soil and groundwater").font(.clCite).foregroundStyle(Palette.muted)
            Chart {
                RectangleMark(xStart: .value("Low", 0), xEnd: .value("High", 100), y: .value("Row", "t"), height: 8)
                    .foregroundStyle(Palette.stateStrong).clipShape(Capsule())
                RuleMark(x: .value("Normal", 50)).foregroundStyle(Palette.muted).lineStyle(StrokeStyle(lineWidth: 1, dash: [2, 2]))
                if let soil {
                    PointMark(x: .value("Soil", soil), y: .value("Row", "t")).symbol(.circle).symbolSize(120).foregroundStyle(DataColor.soil)
                }
                if let groundwater {
                    PointMark(x: .value("Groundwater", groundwater), y: .value("Row", "t")).symbol(.diamond).symbolSize(120).foregroundStyle(DataColor.groundwater)
                }
            }
            .chartXScale(domain: 0...100)
            .chartXAxis(.hidden).chartYAxis(.hidden)
            .frame(height: 22)
            HStack(spacing: 4) {
                Text("driest").font(.clCite).foregroundStyle(Palette.muted)
                Spacer()
                Text("normal").font(.clCite).foregroundStyle(Palette.muted)
                Spacer()
                Text("wettest").font(.clCite).foregroundStyle(Palette.muted)
            }
            FlowLayout(spacing: 10) {
                key(AnyShape(Circle()), DataColor.soil, "Soil \(soil.map { Units.ordinal(Int($0.rounded())) } ?? "–")")
                key(AnyShape(Diamond()), DataColor.groundwater, "Groundwater \(groundwater.map { Units.ordinal(Int($0.rounded())) } ?? "–")")
            }
            if !note.isEmpty { Text(note).font(.clCite).foregroundStyle(Palette.muted).fixedSize(horizontal: false, vertical: true) }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Soil moisture \(soil.map { Units.ordinal(Int($0.rounded())) + " percentile" } ?? "not available"), groundwater \(groundwater.map { Units.ordinal(Int($0.rounded())) + " percentile" } ?? "not available"). 50 is normal.")
    }

    private func key(_ shape: AnyShape, _ color: Color, _ text: String) -> some View {
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

/// Sand, silt and clay as one stacked bar with a key.
struct SoilBar: View {
    let mix: SoilMix
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            GeometryReader { g in
                HStack(spacing: 0) {
                    Rectangle().fill(DataColor.sand).frame(width: g.size.width * mix.sandShare)
                    Rectangle().fill(DataColor.silt).frame(width: g.size.width * mix.siltShare)
                    Rectangle().fill(DataColor.clay)
                }
            }
            .frame(height: 14)
            .clipShape(RoundedRectangle(cornerRadius: Radius.xs, style: .continuous))
            HStack(spacing: 12) {
                ForEach([("Sand", DataColor.sand, mix.sand), ("Silt", DataColor.silt, mix.silt), ("Clay", DataColor.clay, mix.clay)], id: \.0) { name, color, v in
                    HStack(spacing: 4) {
                        RoundedRectangle(cornerRadius: 2).fill(color).frame(width: 10, height: 10)
                            .overlay(RoundedRectangle(cornerRadius: 2).strokeBorder(Palette.lineSoft))
                        Text("\(name) \(Int(v.rounded()))%").font(.clCite).foregroundStyle(Palette.text2)
                    }
                }
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Sand \(Int(mix.sand.rounded())) percent, silt \(Int(mix.silt.rounded())) percent, clay \(Int(mix.clay.rounded())) percent")
        .accessibilityIdentifier("soil-bar")
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
        .clipShape(RoundedRectangle(cornerRadius: Radius.xs, style: .continuous))
        .accessibilityElement()
        .accessibilityLabel("Months: " + months.map(\.label).joined(separator: ", "))
    }
}

struct MonthLetters: View {
    var body: some View {
        HStack(spacing: 2) {
            ForEach(Array("JFMAMJJASOND".enumerated()), id: \.offset) { _, ch in
                Text(String(ch)).font(.clCite).foregroundStyle(Palette.muted).frame(maxWidth: .infinity)
            }
        }
        .accessibilityHidden(true)
    }
}
