import SwiftUI
import Charts

/// "Coming season" (web ComingSeason.tsx): leads with the decision in three items (winter rain, water supply,
/// next season's need), each a plain answer with a small chart. Outlooks, not forecasts. The rest under More detail.
struct SeasonPanel: View {
    let session: FieldSession
    @Environment(AppModel.self) private var app
    @Environment(AppEnvironment.self) private var env

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            SectionHeader("Coming season")
            if let o = session.outlook.value {
                let p = ComingSeasonBuilder.build(outlook: o, field: session.field, nasaNow: session.nasaNow.value,
                                                  strategies: session.currentStrategies, limit: env.limits.limit(for: session.field.id))
                content(p, o)
            } else if let e = session.outlook.error {
                if e == .notFound {
                    Text(session.field.isBC ? "The coming-season outlook is not ready for this field yet." : "Not ready for this field yet.")
                        .font(.clBody).foregroundStyle(Palette.muted).padding(.top, 8)
                } else {
                    ErrorStateView(error: e) { Task { await session.load(force: true) } }
                }
            } else {
                VStack(alignment: .leading, spacing: 12) {
                    AnswerView(answer: Answer(id: "a", question: "Will this winter be wetter or drier than normal?", headline: "NOAA's outlook leans one way this winter", detail: "Nov–Jan leans one way (40% chance).", cite: "NOAA"))
                    AnswerView(answer: Answer(id: "b", question: "Will there be water for next season?", headline: "Reservoirs hold most of their average", detail: "Allocations not announced.", cite: "CDEC"))
                }
                .placeholder(true)
            }
        }
    }

    @ViewBuilder private func content(_ p: ComingSeasonPresentation, _ o: Outlook) -> some View {
        Text(p.lede).font(.clBody).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true).padding(.top, 4)
        AnswerView(answer: p.rain)
        if !p.leans.isEmpty { LeanChart(leans: p.leans).padding(.bottom, 12) }
        Hairline()
        AnswerView(answer: p.water)
        if !p.storage.isEmpty && !session.field.isBC { StorageChart(bars: p.storage).padding(.bottom, 12) }
        Hairline()
        AnswerView(answer: p.need)
        if !p.needBars.isEmpty { NeedChart(bars: p.needBars, limit: p.limit).padding(.bottom, 12) }
        Button { app.select(tab: .compare) } label: { Label("Compare rotations", systemImage: "arrow.left.arrow.right") }
            .buttonStyle(.pill(.tonal)).padding(.top, 8)
        SavedNote(freshness: session.outlook.freshness?.savedAt != nil ? session.outlook.freshness : nil).padding(.top, 8)
        MoreDetailRow(teaser: "Every outlook, bare stretch, allocations").padding(.top, Metrics.sectionGap)
        if app.detailOn {
            VStack(alignment: .leading, spacing: 14) { SeasonDetail(outlook: o, presentation: p) }
                .padding(.top, 8).transition(.opacity)
        }
    }
}

/// The NOAA lean per 3-month season: chance of the favoured third; 33% is no lean.
struct LeanChart: View {
    let leans: [ComingSeasonPresentation.SeasonLean]
    var body: some View {
        Chart(leans) { l in
            BarMark(x: .value("Season", l.label), y: .value("Chance", l.probability))
                .foregroundStyle(l.tilt > 0 ? DataColor.water : l.tilt < 0 ? DataColor.bare : DataColor.noView)
                .annotation(position: .top) {
                    Text(l.tilt > 0 ? "wetter" : l.tilt < 0 ? "drier" : "no lean").font(.clCite).foregroundStyle(Palette.muted)
                }
            RuleMark(y: .value("No lean", 33))
                .foregroundStyle(Palette.mark)
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [3, 3]))
        }
        .chartYScale(domain: 0...70)
        .chartYAxis {
            AxisMarks(values: [0, 33, 50]) { v in
                AxisGridLine().foregroundStyle(Palette.lineSoft)
                AxisValueLabel { if let n = v.as(Int.self) { Text("\(n)%").font(.clCite) } }
            }
        }
        .chartXAxis { AxisMarks { AxisValueLabel().font(.clCite) } }
        .frame(height: 150)
        .safeAreaInset(edge: .bottom, spacing: 6) {
            Text("Bar = chance of the season the outlook favours. Dashed line = 33%, no lean.")
                .font(.clCite).foregroundStyle(Palette.muted).frame(maxWidth: .infinity, alignment: .leading)
        }
        .accessibilityElement()
        .accessibilityLabel(leans.map { "\($0.label): rain \($0.rainWords)" }.joined(separator: ". "))
    }
}

/// Reservoir storage as % of the average for the date; the line is average.
struct StorageChart: View {
    let bars: [ComingSeasonPresentation.StorageBar]
    var body: some View {
        Chart(bars) { b in
            BarMark(x: .value("% of average", b.pctOfAverage), y: .value("Reservoir", b.name), height: 14)
                .foregroundStyle(b.pctOfAverage < 80 ? Palette.warn : DataColor.water)
                .annotation(position: .trailing) { Text("\(Int(b.pctOfAverage.rounded()))%").font(.clCite).foregroundStyle(Palette.text2) }
            RuleMark(x: .value("Average", 100)).foregroundStyle(Palette.mark).lineStyle(StrokeStyle(lineWidth: 1.5))
        }
        .chartXScale(domain: 0...140)
        .chartXAxis {
            AxisMarks(values: [0, 50, 100]) { v in
                AxisGridLine().foregroundStyle(Palette.lineSoft)
                AxisValueLabel { if let n = v.as(Int.self) { Text(n == 100 ? "average" : "\(n)%").font(.clCite) } }
            }
        }
        .chartYAxis { AxisMarks { AxisValueLabel().font(.clCite) } }
        .frame(height: CGFloat(36 * bars.count + 26))
        .accessibilityElement()
        .accessibilityLabel(bars.map(\.text).joined(separator: ". "))
    }
}

/// Next season's irrigation need per rotation (acre-ft/acre), the range across outlook scenarios, and your limit.
struct NeedChart: View {
    let bars: [ComingSeasonPresentation.NeedBar]
    let limit: Double
    var body: some View {
        let top = max(limit, bars.map(\.range.high).max() ?? limit) * 1.15
        Chart {
            ForEach(bars) { b in
                BarMark(x: .value("Acre-feet per acre", b.range.value), y: .value("Rotation", b.isToday ? "\(b.name) (today)" : b.name), height: 12)
                    .foregroundStyle(b.range.value > limit ? Palette.warn : Palette.accent)
                    .annotation(position: .trailing) { Text(Units.oneDecimal(b.range.value)).font(.clCite).foregroundStyle(Palette.text2) }
            }
            RuleMark(x: .value("Your limit", limit))
                .foregroundStyle(Palette.mark)
                .lineStyle(StrokeStyle(lineWidth: 2))
                .annotation(position: .top, alignment: .leading) { Text("your limit \(Units.oneDecimal(limit))").font(.clCite).foregroundStyle(Palette.text) }
        }
        .chartXScale(domain: 0...top)
        .chartXAxis { AxisMarks { AxisGridLine().foregroundStyle(Palette.lineSoft); AxisValueLabel().font(.clCite) } }
        .chartYAxis { AxisMarks { AxisValueLabel().font(.clCite) } }
        .frame(height: CGFloat(34 * bars.count + 40))
        .accessibilityElement()
        .accessibilityLabel("Water need next season, acre-feet per acre: " + bars.map { "\($0.name) \(Units.oneDecimal($0.range.value))" }.joined(separator: ", ") + ". Your limit \(Units.oneDecimal(limit)).")
    }
}

/// Everything else from the outlook file, collapsed.
struct SeasonDetail: View {
    let outlook: Outlook
    let presentation: ComingSeasonPresentation

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            SectionHeader("Season by season")
            ForEach(presentation.leans) { l in
                FactRow(label: l.label, value: "Rain \(l.rainWords). Temperature \(l.tempWords).")
            }
            SourceLine(text: "NOAA Climate Prediction Center. Each season is split into a wetter, a middle and a drier third; 40% means the odds are tilted, not that rain is certain.")
        }
        if let bw = outlook.field?.bareWindow {
            VStack(alignment: .leading, spacing: 6) {
                SectionHeader("Longest bare stretch this winter")
                if let s = GrowerDate.monthDayPart(bw.medianStart), let e = GrowerDate.monthDayPart(bw.medianEnd) {
                    Text("Usually bare from \(s) to \(e), about \(Int((bw.medianDays?.value ?? 0).rounded())) days.").font(.clBody)
                    if let c = outlook.field?.heavyRain?.climatology?.value {
                        Text("A day with 1 inch of rain or more landed in that window in \(Int(c.rounded()))% of past winters\(outlook.field?.heavyRain?.givenOutlook?.value.map { "; about \(Int($0.rounded()))% with this winter's outlook" } ?? "").")
                            .font(.clBody).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
                    }
                } else {
                    Text("Usually covered or flooded all winter: no regular bare stretch.").font(.clBody)
                }
                SourceLine(text: "This field's satellite calendar and NOAA station rain. Past record, not a forecast. \(bareDefinition)")
            }
        }
        if let rows = outlook.allocations?.history?.rows.filter({ $0.partialYear != true }).suffix(6), !rows.isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                SectionHeader("What Shasta storage has meant before")
                Grid(alignment: .leading, horizontalSpacing: 12, verticalSpacing: 4) {
                    GridRow {
                        Text("Mid Nov of").font(.clCite); Text("Shasta full").font(.clCite); Text("Next year, south-of-Delta farms").font(.clCite)
                    }
                    .foregroundStyle(Palette.muted)
                    ForEach(Array(rows)) { r in
                        GridRow {
                            Text(String(r.allocationYear - 1)).font(.clSmallNumber)
                            Text(r.pctOfCapacity.map { "\(Int($0.rounded()))%" } ?? "–").font(.clSmallNumber)
                            Text(r.southAg.map { "\(Int($0))%" } ?? "–").font(.clSmallNumber)
                        }
                    }
                }
                SourceLine(text: "Reclamation CVP allocation table; storage from CDEC. Descriptive only.")
            }
        }
        if let snow = outlook.snow {
            VStack(alignment: .leading, spacing: 4) {
                SectionHeader("Snowpack and spring runoff")
                Text("Statewide snowpack holds \(Units.oneDecimal(snow.statewide?.sweInches?.value ?? 0)) in of water (\(snow.statewide?.reportDate ?? "latest")); the snow season has barely started. DWR's runoff forecast (Bulletin 120) is \(snow.bulletin120?.status ?? "not out yet"); the first usually comes in February.")
                    .font(.clBody).fixedSize(horizontal: false, vertical: true)
            }
        }
        if !outlook.notYetPublished.isEmpty {
            VStack(alignment: .leading, spacing: 4) {
                SectionHeader("Not published yet")
                ForEach(outlook.notYetPublished, id: \.item) { p in
                    Text("\(p.item): \(p.status ?? "not yet")").font(.clSecondary).foregroundStyle(Palette.text2)
                }
            }
        }
        if let s = outlook.plainLanguageSummary {
            VStack(alignment: .leading, spacing: 4) {
                SectionHeader("The whole outlook in one paragraph")
                Text(s).font(.clSecondary).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}
