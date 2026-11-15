import SwiftUI
import Charts

/// "Compare": today's rotation against the top 2 alternatives, as what you gain and give up in acre-feet and days.
struct CompareScreen: View {
    let field: FieldLocation
    @Environment(AppEnvironment.self) private var env
    @State private var model: CompareViewModel?

    var body: some View {
        Group {
            if let model { CompareContent(model: model) } else { Color.clear }
        }
        .task(id: field.id) {
            let m = CompareViewModel(field: field, repository: env.repository, limits: env.limits)
            model = m
            await m.load()
        }
    }
}

private struct CompareContent: View {
    let model: CompareViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                FieldHeader(field: model.field)
                Text("If you switched, what would you gain and what would you give up?")
                    .font(.clHeading)
                    .foregroundStyle(Palette.text)
                    .fixedSize(horizontal: false, vertical: true)
                LimitEditor(model: model)
                if let error = model.error {
                    ErrorStateView(error: error) { Task { await model.load() } }
                } else if let p = model.presentation {
                    content(p)
                } else {
                    Panel { Text("Rice + winter flood").font(.clAnswer); Text("5.2 acre-ft/acre · fits your limit").font(.clBody) }
                        .placeholder(true)
                    Panel { Text("Dry-year safflower").font(.clAnswer); Text("You gain: needs less irrigation water").font(.clBody) }
                        .placeholder(true)
                }
            }
            .padding(Metrics.gutter)
        }
        .background(Palette.paper)
        .refreshable { await model.load() }
    }

    @ViewBuilder private func content(_ p: ComparePresentation) -> some View {
        TodayCard(today: p.today)
        ForEach(p.top) { alt in
            AlternativeCard(alt: alt, today: p.today, limit: model.limit.value)
        }
        NavigationLink {
            AllOptionsView(options: p.all, limit: model.limit.value, field: model.field)
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("See all options").font(.clBodyStrong).foregroundStyle(Palette.text)
                    Text("Every rotation, every factor, side by side").font(.clCite).foregroundStyle(Palette.muted)
                }
                Spacer()
                Image(systemName: "chevron.right").foregroundStyle(Palette.muted)
            }
            .padding(12)
            .overlay(RoundedRectangle(cornerRadius: Metrics.radius).strokeBorder(Palette.line))
        }
        .accessibilityIdentifier("see-all-options")
        SavedNote(freshness: model.freshness)
        MoreDetail {
            VStack(alignment: .leading, spacing: 8) {
                SectionHeading(text: "How this comparison works")
                Text("A gain or a give-up counts only when the likely ranges of the two rotations don't overlap; otherwise the inputs aren't precise enough to say which is better. Water need comes from the rotation model with NASA POWER weather, 2015–2025. Today's bare days are what the satellites saw; the alternatives' are estimated by the model.")
                    .font(.clBody).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
                Text(p.openETLine).font(.clBody).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
                SourceLine(text: "Rotation engine (backend/engine); OpenET Ensemble v2.1 for the water check. \(bareDefinition) Supports, doesn't replace, your adviser.")
            }
            FieldDetailSections(field: model.field)
        }
    }
}

/// The grower's water limit for this field: stored on the phone, sent to the engine for re-scoring.
private struct LimitEditor: View {
    let model: CompareViewModel
    @State private var draft: Double = 0

    var body: some View {
        let limit = model.limit
        Panel {
            HStack(alignment: .firstTextBaseline) {
                Text("Your water limit").font(.clLabel).foregroundStyle(Palette.muted)
                Spacer()
                if model.isRescoring {
                    ProgressView().controlSize(.small)
                    Text("Re-scoring").font(.clCite).foregroundStyle(Palette.muted)
                }
            }
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text("\(Units.oneDecimal(draft)) acre-ft/acre")
                    .font(.custom(FontName.slabSemibold, size: 24, relativeTo: .title2).monospacedDigit())
                    .foregroundStyle(Palette.text)
                    .accessibilityIdentifier("limit-value")
                if limit.isExample {
                    Text("example, change to yours")
                        .font(.clCiteItalic)
                        .foregroundStyle(Palette.warn)
                }
            }
            HStack(spacing: 12) {
                Slider(value: $draft, in: WaterLimitStore.range, step: 0.1) { editing in
                    if !editing { model.setLimit(draft) }
                }
                .accessibilityLabel("Water limit")
                .accessibilityValue("\(Units.oneDecimal(draft)) acre-feet per acre")
                Stepper("Water limit", value: Binding(get: { draft }, set: { draft = $0; model.setLimit($0) }),
                        in: WaterLimitStore.range, step: 0.1)
                    .labelsHidden()
                    .accessibilityIdentifier("limit-stepper")
            }
            HStack {
                Text("Acre-feet per acre a year, from your district, GSA or well. Saved on this phone for this field.")
                    .font(.clCite).foregroundStyle(Palette.muted).fixedSize(horizontal: false, vertical: true)
                if !limit.isExample {
                    Button("Use example") { model.resetLimit(); draft = model.limit.value }
                        .font(.clCite)
                }
            }
            if let e = model.rescoreError, !model.isRescoring {
                Text("Couldn't re-score with the server (\(e.title.lowercased())); showing the saved scores.")
                    .font(.clCite).foregroundStyle(Palette.bad)
            }
        }
        .onAppear { draft = limit.value }
        .onChange(of: model.field.id) { draft = model.limit.value }
    }
}

private struct TodayCard: View {
    let today: RotationSummary
    var body: some View {
        Panel {
            Text("What you do now").font(.clLabel).foregroundStyle(Palette.muted)
            Text(today.name).font(.clAnswer).foregroundStyle(Palette.text)
            MonthStrip(months: today.months)
            MonthLetters()
            if let w = today.water {
                Text("Needs about \(Units.oneDecimal(w.value)) acre-ft/acre a year · \(today.fit.text.lowercased())")
                    .font(.clBody).foregroundStyle(today.fit == .fits ? Palette.text2 : Palette.warn)
            }
            if let b = today.bareDays {
                Text("Bare about \(Int(b.value.rounded())) days a year\(today.bareDaysSeen ? ", as seen by satellite" : ", estimated")")
                    .font(.clSecondary).foregroundStyle(Palette.text2)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("today-card")
    }
}

private struct AlternativeCard: View {
    let alt: AlternativeComparison
    let today: RotationSummary
    let limit: Double

    var body: some View {
        Panel {
            Text("Instead: \(alt.option.name)").font(.clAnswer).foregroundStyle(Palette.text)
            MonthStrip(months: alt.option.months)
            MonthLetters()
            if let w = alt.option.water {
                Text("\(Units.oneDecimal(w.value)) acre-ft/acre a year · \(alt.option.fit.text.lowercased())")
                    .font(.clSecondary).foregroundStyle(alt.option.fit == .fits ? Palette.text2 : Palette.warn)
            }
            if let a = alt.option.water, let b = today.water {
                WaterRangeChart(today: b, option: a, limit: limit)
            }
            tradeList("You gain", alt.gains, color: Palette.accent, empty: "Nothing clearly better than today.")
            tradeList("You give up", alt.losses, color: Palette.warn, empty: "Nothing clearly worse than today.")
            if !alt.unclear.isEmpty {
                Text("No clear difference: \(alt.unclear.joined(separator: ", ").lowercased()).")
                    .font(.clCite).foregroundStyle(Palette.muted)
            }
        }
        .accessibilityIdentifier("alt-\(alt.id)")
    }

    private func tradeList(_ title: String, _ lines: [TradeLine], color: Color, empty: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.clHeading).foregroundStyle(color)
            if lines.isEmpty {
                Text(empty).font(.clSecondary).foregroundStyle(Palette.muted)
            }
            ForEach(lines) { l in
                VStack(alignment: .leading, spacing: 1) {
                    Text(l.title).font(.clBodyStrong).foregroundStyle(Palette.text)
                    Text(l.delta).font(.clSecondary).foregroundStyle(Palette.text2)
                }
                .accessibilityElement(children: .combine)
            }
        }
    }
}

/// Today vs this option: likely range of irrigation water, with the limit line.
private struct WaterRangeChart: View {
    let today: NumRange
    let option: NumRange
    let limit: Double

    var body: some View {
        let top = max(limit, today.high, option.high) * 1.12
        Chart {
            row("Today", today, Palette.muted)
            row("This", option, Palette.accent)
            RuleMark(x: .value("Your limit", limit))
                .foregroundStyle(Palette.mark).lineStyle(StrokeStyle(lineWidth: 2))
                .annotation(position: .top, alignment: .center) { Text("limit").font(.clCite).foregroundStyle(Palette.text) }
        }
        .chartXScale(domain: 0...top)
        .chartXAxis { AxisMarks(values: .automatic(desiredCount: 4)) { AxisGridLine().foregroundStyle(Palette.lineSoft); AxisValueLabel().font(.clCite) } }
        .chartYAxis { AxisMarks { AxisValueLabel().font(.clCite) } }
        .frame(height: 92)
        .accessibilityElement()
        .accessibilityLabel("Irrigation water, acre-feet per acre a year. Today \(Units.oneDecimal(today.value)), this option \(Units.oneDecimal(option.value)), your limit \(Units.oneDecimal(limit)).")
    }

    @ChartContentBuilder private func row(_ name: String, _ r: NumRange, _ color: Color) -> some ChartContent {
        BarMark(xStart: .value("Low", r.low), xEnd: .value("High", max(r.high, r.low + 0.05)), y: .value("Rotation", name), height: 10)
            .foregroundStyle(color.opacity(0.45))
        PointMark(x: .value("Best estimate", r.value), y: .value("Rotation", name))
            .symbol(.circle).symbolSize(50).foregroundStyle(color)
    }
}

private struct MonthLetters: View {
    var body: some View {
        HStack(spacing: 2) {
            ForEach(Array("JFMAMJJASOND".enumerated()), id: \.offset) { _, ch in
                Text(String(ch)).font(.clCite).foregroundStyle(Palette.muted).frame(maxWidth: .infinity)
            }
        }
        .accessibilityHidden(true)
    }
}

/// Every rotation, every factor.
struct AllOptionsView: View {
    let options: [RotationSummary]
    let limit: Double
    let field: FieldLocation

    var body: some View {
        List {
            Section {
                ForEach(options) { o in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack(alignment: .firstTextBaseline) {
                            Text(o.name + (o.isToday ? " (today)" : "")).font(.clAnswer)
                            Spacer()
                            if let r = o.rank { Text("rank \(r)").font(.clCite).foregroundStyle(Palette.muted) }
                        }
                        Text(o.fullName).font(.clCite).foregroundStyle(Palette.muted)
                        MonthStrip(months: o.months)
                        if let w = o.water {
                            FactRow(label: "Water", value: "\(Units.oneDecimal(w.value)) acre-ft/acre a year", note: w.hasSpread ? "likely \(Units.oneDecimal(w.low))–\(Units.oneDecimal(w.high)); \(o.fit.text.lowercased())" : o.fit.text, warn: o.fit != .fits)
                        }
                        if let b = o.bareDays {
                            FactRow(label: "Bare", value: "\(Int(b.value.rounded())) days a year", note: o.bareDaysSeen ? "seen by satellite" : "estimated")
                        }
                        if let r = o.rainOnBareDays {
                            FactRow(label: "Heavy rain on bare soil", value: String(format: "%.1f days a year", r.value))
                        }
                        ForEach(o.scores) { s in
                            FactRow(label: s.label, value: "\(Int(s.value.value.rounded())) of 100")
                        }
                    }
                    .padding(.vertical, 6)
                    .listRowBackground(o.isToday ? Palette.accentSoft : Palette.paper)
                }
            } footer: {
                Text("Your limit: \(Units.oneDecimal(limit)) acre-ft/acre. Scores of 0 to 100 are rules of thumb from the rotation engine, higher is better; rank uses equal weights. Dollars per acre aren't scored yet.")
                    .font(.clCite)
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(Palette.paper)
        .navigationTitle("All options")
        .navigationBarTitleDisplayMode(.inline)
    }
}
