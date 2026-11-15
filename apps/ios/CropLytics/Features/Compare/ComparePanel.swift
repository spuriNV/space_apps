import SwiftUI
import Charts

/// "Compare" (web ComparePanel.tsx): what you'd gain and give up against today, in acre-feet and days.
/// Today's rotation vs the top 2 alternatives; weather replays; your water limit; your priorities and what-ifs,
/// re-scored by the rotation engine through POST /score; "See all options".
struct ComparePanel: View {
    let session: FieldSession
    @Environment(AppModel.self) private var app
    @Environment(AppEnvironment.self) private var env
    @State private var allOpen = false
    @State private var tuneOpen = false

    var body: some View {
        @Bindable var session = session
        let limit = env.limits.limit(for: session.field.id)
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader("If you switched, what would you gain and give up?")
            LimitEditor(session: session)
            PillSegmented(label: "Weather", options: CompareBuilder.Weather.allCases.map { ($0, $0.short) }, selection: $session.weather)
                .accessibilityIdentifier("weather")
            Button {
                withAnimation { tuneOpen.toggle() }
            } label: {
                Label(tuneOpen ? "Hide priorities and what-ifs" : "Your priorities, and what if it's drier or hotter", systemImage: "slider.horizontal.3")
            }
            .buttonStyle(.pill(.text, small: true))
            .accessibilityIdentifier("tune")
            if tuneOpen { TunePanel(session: session).transition(.opacity) }

            if let strategies = session.currentStrategies,
               let p = CompareBuilder.build(strategies: strategies, calendar: session.calendar.value, limit: limit.value, weather: session.weather) {
                TodaySummary(today: p.today)
                ForEach(p.top) { alt in AlternativeSection(alt: alt, today: p.today, limit: limit.value, weather: session.weather) }
                Button { allOpen = true } label: { Label("See all options", systemImage: "list.bullet") }
                    .buttonStyle(.pill(.outline, fullWidth: true))
                    .accessibilityIdentifier("see-all-options")
                Button { app.select(tab: .print) } label: { Label("Print this comparison for your adviser", systemImage: "printer") }
                    .buttonStyle(.pill(.primary, fullWidth: true))
                SavedNote(freshness: session.scoredFreshness ?? (session.strategies.freshness?.savedAt != nil ? session.strategies.freshness : nil))
                MoreDetailRow(teaser: "How the options are ranked").padding(.top, 12)
                if app.detailOn {
                    VStack(alignment: .leading, spacing: 8) {
                        SectionHeader("How this comparison works")
                        Text("A gain or a give-up counts only when the likely ranges of the two rotations don't overlap; otherwise the inputs aren't precise enough to say which is better. Water need comes from the rotation model with NASA POWER weather, 2015–2025; the dry and wet years replay 2022 and 2023. Today's bare days are what the satellites saw; the alternatives' are estimated.")
                            .font(.clBody).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
                        Text(p.openETLine).font(.clBody).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
                        SourceLine(text: "Rotation engine; OpenET Ensemble v2.1 for the water check. \(bareDefinition) Supports, doesn't replace, your adviser.")
                    }
                    .transition(.opacity)
                }
                Color.clear.frame(height: 1).sheet(isPresented: $allOpen) {
                    NavigationStack {
                        AllOptionsView(options: p.all, limit: limit.value, field: session.field)
                            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done") { allOpen = false } } }
                    }
                    .presentationDetents([.large])
                }
            } else if let e = session.strategies.error {
                ErrorStateView(error: e) { Task { await session.load(force: true) } }
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Rice + winter flood").font(.clAnswer); Text("5.2 acre-ft/acre · fits your limit").font(.clBody)
                    Text("Dry-year safflower").font(.clAnswer); Text("You gain: needs less irrigation water").font(.clBody)
                }
                .placeholder(true)
            }
        }
        .onAppear { session.limitForScoring = limit.value }
    }
}

/// The grower's water limit for this field: saved on the phone, re-scored by the engine.
private struct LimitEditor: View {
    let session: FieldSession
    @Environment(AppEnvironment.self) private var env
    @State private var draft: Double = 0

    var body: some View {
        let limit = env.limits.limit(for: session.field.id)
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline) {
                Text("Your water limit").font(.clLabel).foregroundStyle(Palette.muted)
                Spacer()
                if session.isRescoring {
                    ProgressView().controlSize(.small)
                    Text("Re-scoring").font(.clCite).foregroundStyle(Palette.muted)
                }
            }
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text("\(Units.oneDecimal(draft)) acre-ft/acre").font(.clNumber).foregroundStyle(Palette.text)
                    .contentTransition(.numericText())
                    .accessibilityIdentifier("limit-value")
                if limit.isExample { StatusWord(kind: .example, text: "example, change to yours") }
            }
            HStack(spacing: 12) {
                Slider(value: $draft, in: WaterLimitStore.range, step: 0.1) { editing in if !editing { commit(draft) } }
                    .accessibilityLabel("Water limit")
                    .accessibilityValue("\(Units.oneDecimal(draft)) acre-feet per acre")
                Stepper("Water limit", value: Binding(get: { draft }, set: { draft = $0; commit($0) }), in: WaterLimitStore.range, step: 0.1)
                    .labelsHidden()
                    .accessibilityIdentifier("limit-stepper")
            }
            HStack {
                Text("Acre-feet per acre a year, from your district, GSA or well. Saved on this phone.")
                    .font(.clCite).foregroundStyle(Palette.muted).fixedSize(horizontal: false, vertical: true)
                if !limit.isExample {
                    Button("Use example") { env.limits.reset(session.field.id); draft = env.limits.limit(for: session.field.id).value; session.scheduleRescore(limit: draft) }
                        .buttonStyle(.pill(.text, small: true))
                }
            }
            if let e = session.rescoreError, !session.isRescoring {
                Text("Couldn't re-score with the server (\(e.title.lowercased())); showing the saved scores.").font(.clCite).foregroundStyle(Palette.bad)
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: Radius.md, style: .continuous).fill(Palette.panel2))
        .onAppear { draft = limit.value }
    }

    private func commit(_ v: Double) {
        env.limits.set(v, for: session.field.id)
        session.scheduleRescore(limit: env.limits.limit(for: session.field.id).value)
    }
}

/// What matters to you (0-4 per priority) and what if the year is drier or hotter; ranked by the engine.
private struct TunePanel: View {
    let session: FieldSession
    static let levels = ["None", "Normal", "More", "Much", "Top"]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("What matters to you").font(.clLabel).foregroundStyle(Palette.text)
            ForEach(FieldSession.priorityKeys, id: \.key) { p in
                VStack(alignment: .leading, spacing: 4) {
                    Text(p.label).font(.clSecondary).foregroundStyle(Palette.text2)
                    PillSegmented(label: p.label, options: Self.levels.enumerated().map { ($0.offset, $0.element) },
                                  selection: Binding(get: { session.weight(p.key) }, set: { session.weights[p.key] = $0 }))
                }
            }
            Text("What if the year is").font(.clLabel).foregroundStyle(Palette.text).padding(.top, 4)
            PillSegmented(label: "Rain", options: [(-20.0, "20% less rain"), (0.0, "Normal rain"), (20.0, "20% more rain")],
                          selection: Binding(get: { session.scenario.dP_pct }, set: { session.scenario.dP_pct = $0 }))
                .accessibilityIdentifier("rain-whatif")
            PillSegmented(label: "Heat", options: [(0.0, "Normal heat"), (2.0, "4 °F warmer"), (4.0, "7 °F warmer")],
                          selection: Binding(get: { session.scenario.dT_c }, set: { session.scenario.dT_c = $0 }))
            Text(session.isRescoring ? "Re-scoring…" : session.isCustomScoring ? "Water need and ranking below use your settings." : "Default: every priority counts the same, normal weather.")
                .font(.clCite).foregroundStyle(Palette.muted)
            if let ranked = session.currentStrategies?.sorted(by: { ($0.composite?.value ?? 0) > ($1.composite?.value ?? 0) }) {
                Text("Best fit for what matters to you").font(.clLabel).foregroundStyle(Palette.text).padding(.top, 4)
                ForEach(Array(ranked.enumerated()), id: \.element.id) { i, s in
                    let tie = i == 0 && ranked.count > 1 && (ranked[0].composite?.low ?? 0) <= (ranked[1].composite?.high ?? 0)
                    Text("\(i + 1). \(FieldNaming.shortRotationName(s))\(s.isBaseline ? " (today)" : "")\(tie ? ", too close to call with the next one" : "")")
                        .font(.clSecondary).foregroundStyle(s.isBaseline ? Palette.accent : Palette.text2)
                }
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: Radius.md, style: .continuous).fill(Palette.panel2))
        .accessibilityIdentifier("tune-panel")
    }
}

private struct TodaySummary: View {
    let today: RotationSummary
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("What you do now").font(.clSecondary).foregroundStyle(Palette.muted)
            Text(today.name).font(.clAnswer).foregroundStyle(Palette.text)
            MonthStrip(months: today.months)
            MonthLetters()
            Text("\(today.rainFed ? today.waterText : "Needs about \(today.waterText) a year") · \(today.fit.text.lowercased())")
                .font(.clBody).foregroundStyle(today.fit == .fits ? Palette.text2 : Palette.warn)
            if let b = today.bareDays {
                Text("Bare about \(Int(b.value.rounded())) days a year\(today.bareDaysSeen ? ", as seen by satellite" : ", estimated")")
                    .font(.clSecondary).foregroundStyle(Palette.text2)
            }
        }
        .padding(.vertical, 8)
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("today-card")
    }
}

private struct AlternativeSection: View {
    let alt: AlternativeComparison
    let today: RotationSummary
    let limit: Double
    let weather: CompareBuilder.Weather

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Hairline()
            Text("Instead: \(alt.option.name)").font(.clAnswer).foregroundStyle(Palette.text).padding(.top, 8)
            MonthStrip(months: alt.option.months)
            MonthLetters()
            Text("\(alt.option.waterText) a year · \(alt.option.fit.text.lowercased())")
                .font(.clSecondary).foregroundStyle(alt.option.fit == .fits ? Palette.text2 : Palette.warn)
            if let a = alt.option.water, let b = today.water, !alt.option.rainFed {
                WaterRangeChart(today: b, option: a, limit: limit)
            }
            trade("You gain", alt.gains, Palette.accent, "Nothing clearly better than today.")
            trade("You give up", alt.losses, Palette.warn, "Nothing clearly worse than today.")
            if !alt.unclear.isEmpty {
                Text("No clear difference: \(alt.unclear.joined(separator: ", ").lowercased()).").font(.clCite).foregroundStyle(Palette.muted)
            }
        }
        .accessibilityIdentifier("alt-\(alt.id)")
    }

    private func trade(_ title: String, _ lines: [TradeLine], _ color: Color, _ empty: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.clHeading).foregroundStyle(color)
            if lines.isEmpty { Text(empty).font(.clSecondary).foregroundStyle(Palette.muted) }
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
struct WaterRangeChart: View {
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

/// Every rotation, every factor.
struct AllOptionsView: View {
    let options: [RotationSummary]
    let limit: Double
    let field: FieldLocation

    var body: some View {
        List {
            Section {
                ForEach(options) { o in OptionRow(o: o) }
            } footer: {
                Text("Your limit: \(Units.oneDecimal(limit)) acre-ft/acre. Scores of 0 to 100 are rules of thumb from the rotation engine, higher is better. Dollars per acre aren't scored yet.")
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

private struct OptionRow: View {
    let o: RotationSummary

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                Text(title).font(.clAnswer)
                Spacer()
                if let r = o.rank { Text("rank \(r)").font(.clCite).foregroundStyle(Palette.muted) }
            }
            Text(o.fullName).font(.clCite).foregroundStyle(Palette.muted)
            MonthStrip(months: o.months)
            FactRow(label: "Water", value: o.rainFed ? o.waterText : "\(o.waterText) a year", note: waterNote, warn: o.fit != .fits)
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
        .listRowBackground(o.isToday ? Palette.accentContainer : Palette.paper)
    }

    private var title: String { o.isToday ? o.name + " (today)" : o.name }

    private var waterNote: String {
        guard let w = o.water, w.hasSpread, !o.rainFed else { return o.fit.text }
        let range = "likely " + Units.oneDecimal(w.low) + "–" + Units.oneDecimal(w.high)
        return range + "; " + o.fit.text.lowercased()
    }
}
