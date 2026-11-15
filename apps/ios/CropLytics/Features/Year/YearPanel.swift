import SwiftUI

/// "This field's year" (web YearSheet.tsx): a typical-year strip, one strip per season, heavy-rain days marked, replay
/// on the map, and (with More detail) the machine-learning calendar, OPERA standing water and crop-stress weeks.
/// Tap a square to move the viewing date there.
struct YearPanel: View {
    let session: FieldSession
    @Environment(AppModel.self) private var app
    @State private var compareML = false
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        @Bindable var app = app
        VStack(alignment: .leading, spacing: 10) {
            SectionHeader("This field's year")
            if let cal = session.calendar.value {
                let p = YearBuilder.build(field: session.field, calendar: cal, ml: session.calendarML.value, models: session.models.value,
                                          daily: session.daily.value, stress: session.stress.value, waterSeen: session.waterSeen.value,
                                          today: app.today, earlier: app.showEarlier, detail: app.detailOn)
                Text(p.lede).font(.clBody).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 8) {
                    Button { app.toggleReplay() } label: {
                        Label(app.playing ? "Pause" : "Replay on the map", systemImage: app.playing ? "pause.fill" : "play.fill")
                    }
                    .buttonStyle(.pill(.primary, small: true))
                    .accessibilityIdentifier("play")
                    if !app.isToday {
                        Button("Back to today") { app.backToToday() }.buttonStyle(.pill(.outline, small: true))
                    }
                }
                if app.detailOn {
                    PillSegmented(label: "Calendar", options: [(false, "Satellite rule"), (true, "Compare with ML")], selection: $compareML,
                                  disabled: p.mlVerdict.available ? [] : [true])
                        .accessibilityIdentifier("ml-toggle")
                    if compareML || !p.mlVerdict.available {
                        (Text("Machine learning: \(p.mlVerdict.short.lowercased()). ").font(.clLabel) + Text(p.mlVerdict.long).font(.clSecondary))
                            .foregroundStyle(p.mlVerdict.warn ? Palette.warn : Palette.text2)
                            .fixedSize(horizontal: false, vertical: true)
                            .accessibilityIdentifier("ml-note")
                    }
                }
                legend
                header
                stripRow(title: "Typical year", sub: p.typicalLabel, strip: p.typical, ml: nil, ticks: [], current: false,
                         bare: p.typicalBareDays.map(String.init) ?? "–", rain: "", year: nil)
                ForEach(p.rows) { r in
                    stripRow(title: String(r.year), sub: r.crop, strip: r.strip, ml: compareML && app.detailOn ? r.ml : nil, ticks: r.ticks,
                             current: r.year == app.t.year, bare: r.bareDays.map(String.init) ?? "–", rain: r.rainOnBare, year: r.year)
                }
                events
                if app.detailOn {
                    Button(app.showEarlier ? "Show only the last 4 seasons" : "Show earlier years (2016–\(String(app.today.year - 4)))") { app.showEarlier.toggle() }
                        .buttonStyle(.pill(.text, small: true))
                        .accessibilityIdentifier("earlier")
                }
                SourceLine(text: "\(FieldNowBuilder.satelliteName(cal)), every 10 days, whole field. Rain from NASA GPM IMERG. \(bareDefinition)")
                MoreDetailRow(teaser: "Machine learning, earlier years").padding(.top, 12)
            } else if let e = session.calendar.error {
                ErrorStateView(error: e) { Task { await session.load(force: true) } }
            } else {
                VStack(alignment: .leading, spacing: 8) { ForEach(0..<4, id: \.self) { _ in SeasonStripView(classes: Array(repeating: .covered, count: 36)) } }
                    .placeholder(true)
            }
        }
    }

    private var legend: some View {
        FlowLayout(spacing: 10) {
            ForEach([CoverClass.covered, .partial, .bare, .water, .noView], id: \.self) { c in
                HStack(spacing: 4) {
                    RoundedRectangle(cornerRadius: 2).fill(SeasonStripView.color(c).opacity(c == .noView ? 0.5 : 1)).frame(width: 10, height: 10)
                    Text(c == .covered ? "Crop growing" : c == .water ? "Flooded" : c.label).font(.clCite).foregroundStyle(Palette.muted)
                }
            }
            HStack(spacing: 4) { Circle().fill(Color(hex: 0x1D3A9E)).frame(width: 7, height: 7); Text("1 in of rain on bare ground").font(.clCite).foregroundStyle(Palette.muted) }
            HStack(spacing: 4) { Circle().strokeBorder(Color(hex: 0x1D3A9E)).frame(width: 7, height: 7); Text("on a crop or water").font(.clCite).foregroundStyle(Palette.muted) }
            if app.detailOn {
                HStack(spacing: 4) { Rectangle().fill(DataColor.water).frame(width: 10, height: 3); Text("Standing water (NASA OPERA)").font(.clCite).foregroundStyle(Palette.muted) }
                HStack(spacing: 4) { Image(systemName: "triangle.fill").font(.system(size: 7)).foregroundStyle(Palette.bad).rotationEffect(.degrees(180)); Text("Crop-stress week").font(.clCite).foregroundStyle(Palette.muted) }
            }
        }
        .accessibilityHidden(true)
    }

    private var header: some View {
        HStack(alignment: .bottom) {
            Spacer()
            Text("Bare days").frame(width: 48)
            Text("1 in rain on bare").frame(width: 62)
        }
        .font(.clCite).foregroundStyle(Palette.muted).multilineTextAlignment(.trailing)
        .accessibilityHidden(true)
    }

    private func stripRow(title: String, sub: String, strip: [CoverClass], ml: [CoverClass]?, ticks: [StripTick], current: Bool,
                          bare: String, rain: String, year: Int?) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .firstTextBaseline, spacing: 6) {
                Text(title).font(current ? .clBodyBold : .clBodyStrong).foregroundStyle(current ? Palette.accent : Palette.text)
                Text(sub).font(.clCite).foregroundStyle(Palette.muted).lineLimit(1)
                Spacer()
                Text(bare).font(.clSmallNumber).frame(width: 48, alignment: .trailing)
                Text(rain).font(.clSmallNumber).frame(width: 62, alignment: .trailing)
            }
            if let year {
                TappableStrip(classes: strip, marker: current ? app.t.dekad : nil, ticks: ticks) { d in
                    app.stopReplay(); app.setDate(TimePoint(year: year, dekad: d))
                }
                if let ml {
                    SeasonStripView(classes: ml, height: 10).opacity(0.9)
                    Text("machine learning").font(.clCite).foregroundStyle(Palette.muted)
                }
            } else {
                SeasonStripView(classes: strip, height: 18)
            }
        }
        .padding(.vertical, 4)
        .padding(.horizontal, current ? 8 : 0)
        .background(RoundedRectangle(cornerRadius: Radius.sm, style: .continuous).fill(current ? Palette.accentContainer.opacity(0.6) : .clear))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title): \(sub). Bare days \(bare). \(SeasonStripView.describe(strip))")
        .accessibilityIdentifier(year.map { "year-\($0)" } ?? "year-typical")
    }

    @ViewBuilder private var events: some View {
        let evs = session.field.events.filter { $0.short != nil || $0.type != nil }
        if !evs.isEmpty {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(evs) { e in
                        Button(e.short ?? GrowerDate.short(e.date) ?? e.date) {
                            if let t = TimePoint(iso: e.date) { app.stopReplay(); app.setDate(t) }
                        }
                        .buttonStyle(.pill(.outline, small: true))
                    }
                }
            }
        }
    }
}
