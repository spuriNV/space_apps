import SwiftUI

/// "Your field now" (web FieldPanel): next steps as a pill row (primary first), the glance card, plain answers,
/// the BC cards, then More detail (NASA data, about the ground, the last 3 seasons, events, sources).
struct FieldNowPanel: View {
    let session: FieldSession
    @Environment(AppModel.self) private var app
    @Environment(AppEnvironment.self) private var env

    var body: some View {
        let p = FieldNowBuilder.build(.init(
            field: session.field, nasaNow: session.nasaNow.value, calendar: session.calendar.value,
            strategies: session.currentStrategies, limit: env.limits.limit(for: session.field.id), t: app.t, today: app.today,
            daily: session.daily.value, stress: session.stress.value, waterSeen: session.waterSeen.value))
        VStack(alignment: .leading, spacing: 0) {
            ActionPills()
                .padding(.horizontal, -Metrics.gutter)
                .padding(.bottom, 8)
            SectionHeader(p.heading)
            GlanceCard(field: session.field, summary: p.summary)
                .placeholder(session.isLoadingCore)
                .padding(.top, 8)
            AnswerList(answers: p.answers.filter { app.detailOn || !$0.detailOnly })
                .placeholder(session.isLoadingCore)
                .padding(.top, 8)
            SavedNote(freshness: session.freshness).padding(.vertical, 6)
            if session.field.isBC {
                FirstNationsCard(session: session).padding(.top, Metrics.sectionGap)
                SalmonPanel(session: session)
            }
            MoreDetailRow(teaser: "Sources, past seasons, 3D").padding(.top, Metrics.sectionGap)
            if app.detailOn {
                FieldDetail(session: session).transition(.opacity)
            }
            Text("CropLytics helps the grower and adviser decide; it does not replace either.")
                .font(.clCite).foregroundStyle(Palette.muted).padding(.top, Metrics.sectionGap)
        }
    }
}

/// Next steps in the grower's words, as a sideways pill row; one primary: the summary for the adviser.
struct ActionPills: View {
    @Environment(AppModel.self) private var app
    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                Button { app.select(tab: .print) } label: { Label("Print for your adviser", systemImage: "printer") }
                    .buttonStyle(.pill(.primary, small: true)).accessibilityIdentifier("go-print")
                Button("What's likely this winter") { app.select(tab: .season) }.buttonStyle(.pill(.tonal, small: true))
                Button("This field's year") { app.select(tab: .year) }.buttonStyle(.pill(.tonal, small: true))
                Button("Compare rotations") { app.select(tab: .compare) }.buttonStyle(.pill(.tonal, small: true))
            }
            .padding(.horizontal, Metrics.gutter).padding(.vertical, 4)
        }
    }
}

/// The glance card: thumbnail, this year's strip with the date marker, the stage, then the four readings.
struct GlanceCard: View {
    let field: FieldLocation
    let summary: FieldNowPresentation.Summary
    @Environment(\.dynamicTypeSize) private var typeSize

    var body: some View {
        Card {
            HStack(alignment: .top, spacing: 12) {
                FieldThumbnail(field: field, size: CGSize(width: 96, height: 66))
                VStack(alignment: .leading, spacing: 4) {
                    Text("\(String(summary.stripYear)) so far").font(.clCite).foregroundStyle(Palette.muted)
                    SeasonStripView(classes: summary.strip, marker: summary.marker, height: 14)
                    StripMonths()
                    Text(summary.stage).font(.clAnswer).foregroundStyle(Palette.text)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityLabel("On the field: \(summary.stage)")
                }
            }
            Hairline()
            if typeSize.isAccessibilitySize {
                VStack(alignment: .leading, spacing: 14) { readings }
            } else {
                Grid(alignment: .topLeading, horizontalSpacing: 16, verticalSpacing: 14) {
                    GridRow { meter(summary.rain, "Rain since 1 Oct"); meter(summary.water, "Water need, a year") }
                    GridRow { meter(summary.greenness, "Greenness"); PercentileTrack(soil: summary.soilPercentile, groundwater: summary.groundwaterPercentile) }
                }
            }
        }
        .accessibilityIdentifier("glance")
    }

    @ViewBuilder private var readings: some View {
        meter(summary.rain, "Rain since 1 Oct")
        meter(summary.water, "Water need, a year")
        meter(summary.greenness, "Greenness")
        PercentileTrack(soil: summary.soilPercentile, groundwater: summary.groundwaterPercentile)
    }

    @ViewBuilder private func meter(_ m: Meter?, _ fallback: String) -> some View {
        if let m {
            MeterView(meter: m).frame(maxWidth: .infinity, alignment: .leading)
        } else {
            VStack(alignment: .leading, spacing: 4) {
                Text(fallback).font(.clCite).foregroundStyle(Palette.muted)
                Text("Not available").font(.clSecondary).italic().foregroundStyle(Palette.muted)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

/// More detail on the field: NASA data (with the ISS photo), about the ground, the last 3 seasons, events, sources.
struct FieldDetail: View {
    let session: FieldSession
    @Environment(AppModel.self) private var app

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            SectionHeader("NASA data behind this field").padding(.top, Metrics.sectionGap).accessibilityIdentifier("nasa-section")
            ISSFigure(session: session).padding(.vertical, 8)
            NasaDataList(datasets: session.field.nasaDatasets)
            SectionHeader(title: "About the ground") {
                Button { app.drillOpen = true } label: { Label("Look in 3D", systemImage: "cube") }
                    .buttonStyle(.pill(.text, small: true))
            }
            .padding(.top, Metrics.sectionGap)
            AboutGround(session: session)
            SectionHeader("The last 3 seasons").padding(.top, Metrics.sectionGap)
            LastSeasons(field: session.field, calendar: session.calendar.value, today: app.today)
            let events = session.field.events + (session.field.waterContext?.orders.map { .init(date: $0.date, title: $0.title, url: $0.url, type: $0.kind, short: nil) } ?? [])
            if !events.isEmpty {
                SectionHeader("What happened around here").padding(.top, Metrics.sectionGap)
                Text("Tap one to move the date there.").font(.clSecondary).foregroundStyle(Palette.muted)
                ForEach(events.sorted { $0.date < $1.date }) { e in
                    ChevronRow(title: e.title, subtitle: GrowerDate.short(e.date) ?? e.date, leading: "calendar") {
                        if let t = TimePoint(iso: e.date) { app.stopReplay(); app.setDate(t) }
                    }
                }
            }
            Button { app.sourcesOpen = true } label: { Label("Sources", systemImage: "books.vertical") }
                .buttonStyle(.pill(.text)).padding(.top, 12)
                .accessibilityIdentifier("sources-link")
            DetailChecks(session: session).padding(.top, Metrics.sectionGap)
        }
    }
}

/// Astronaut photo of the valley near the field (NASA Johnson Space Center).
struct ISSFigure: View {
    let session: FieldSession
    var body: some View {
        if let photos = session.iss.value, let p = nearest(photos) {
            VStack(alignment: .leading, spacing: 6) {
                AsyncImage(url: URL(string: "https://croplytics-app.onrender.com/iss/\(session.field.id)/\(p.file)")) { phase in
                    switch phase {
                    case .success(let img): img.resizable().scaledToFill()
                    default: Rectangle().fill(Palette.panel2).overlay(ProgressView())
                    }
                }
                .frame(height: 170).frame(maxWidth: .infinity)
                .clipShape(RoundedRectangle(cornerRadius: Radius.md, style: .continuous))
                .accessibilityLabel("Astronaut photo taken from the International Space Station\(p.date.map { ", \(GrowerDate.short($0) ?? $0)" } ?? "")")
                Text("Seen from the ISS near your field\(p.date.flatMap { GrowerDate.parse($0) }.map { ", \(GrowerDate.monthsFull[GrowerDate.calendar.component(.month, from: $0) - 1]) \(GrowerDate.year($0))" } ?? "").")
                    .font(.clSecondary).foregroundStyle(Palette.text2)
                SourceLine(text: "\(photos.credit ?? "Image courtesy of the Earth Science and Remote Sensing Unit, NASA Johnson Space Center"). Photo \(p.photoID).")
            }
        }
    }

    private func nearest(_ photos: ISSPhotos) -> ISSPhotos.Photo? {
        let c = session.field.centroid
        return photos.photos.min { a, b in
            hypot((a.centerLat ?? 0) - c.lat, (a.centerLon ?? 0) - c.lon) < hypot((b.centerLat ?? 0) - c.lat, (b.centerLon ?? 0) - c.lon)
        }
    }
}

/// About the ground: soil, water, slope, when the field is usually bare, crop insurance.
struct AboutGround: View {
    let session: FieldSession
    var body: some View {
        let f = session.field
        VStack(alignment: .leading, spacing: 0) {
            if let s = FieldNowBuilder.soilFacts(f) {
                FactRow(label: "Soil", value: [s.texture, f.soil?.muname.flatMap { $0.components(separatedBy: ",").first }].compactMap { $0 }.joined(separator: "; "), note: s.source)
                if let mix = s.mix { SoilBar(mix: mix).padding(.vertical, 8) }
                if !s.line.isEmpty { FactRow(label: "Water and salt", value: s.line) }
                if let r = s.rotation { Text(r).font(.clSecondary).foregroundStyle(Palette.text2).padding(.vertical, 6) }
                Hairline()
            }
            if f.isBC, let ctx = f.waterContext {
                FactRow(label: "Watershed", value: ctx.watershed ?? "Not looked up")
                ForEach(ctx.orders.sorted { $0.date > $1.date }) { o in
                    FactRow(label: GrowerDate.short(o.date) ?? o.date, value: (o.kind == "rescission" ? "Order lifted: " : "Order: ") + o.title)
                }
            } else if let w = f.water {
                FactRow(label: "Water", value: (w.isSurface ? "Surface water" : "Groundwater (wells)") + (w.district.map { ", \($0.replacingOccurrences(of: " (U)", with: ""))" } ?? ""),
                        note: w.sgmaStatus?.replacingOccurrences(of: " (U)", with: ""))
            }
            if let slope = f.terrain?.slopeMeanPct?.value {
                let words = slope < 2 ? "Nearly flat" : slope < 5 ? "Gentle slope" : "Sloping"
                let low = f.terrain?.lowSpotFraction?.value.map { "; low spots on about \(Int(($0 * 100).rounded()))% of the field, where water ponds and frost settles" } ?? ""
                FactRow(label: "Slope", value: "\(words), about \(Units.oneDecimal(slope))% on average\(low).",
                        note: "NASA NASADEM elevation, 100 ft squares; radar reads 1 to 2% even on a levelled field.")
            }
            if let bare = session.calendar.value?.observedBareDays() {
                FactRow(label: "Usually bare", value: "About \(bare.days) days a year", note: "Seen by satellite, \(bare.years.map(String.init).joined(separator: ", ")). \(bareDefinition)")
            }
            if let p = session.insurance.value, let line = DetailLines.insurance(p) {
                FactRow(label: "Crop insurance", value: line, note: "USDA Risk Management Agency, county totals, not this farm.")
            } else if let g = f.gap("insurance") {
                FactRow(label: "Crop insurance", value: "Not available in BC.", note: g.reason)
            }
        }
    }
}

/// The last 3 processed seasons, one line and one strip each.
struct LastSeasons: View {
    let field: FieldLocation
    let calendar: FieldCalendar?
    let today: TimePoint
    var body: some View {
        if let cal = calendar, let last = cal.lastYear {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(Array(((last - 2)...last).reversed()), id: \.self) { y in
                    let s = cal.classes(for: y)
                    let n = { (c: CoverClass) in s.filter { $0 == c }.count * 10 }
                    VStack(alignment: .leading, spacing: 4) {
                        HStack(alignment: .firstTextBaseline) {
                            Text(String(y)).font(.clBodyStrong)
                            Text("\(FieldNaming.cropName(field.cropHistory[String(y)])). Green about \(n(.covered)) days, thin \(n(.partial)), bare \(n(.bare)), flooded \(n(.water))\(n(.noView) > 0 ? ", no clear view \(n(.noView))" : "").")
                                .font(.clSecondary).foregroundStyle(Palette.text2)
                        }
                        SeasonStripView(classes: s, height: 8)
                    }
                }
                if today.year > last {
                    Text("\(String(today.year)): not processed yet. Satellite imagery and the crop map for \(String(today.year)) are still to come.")
                        .font(.clSecondary).foregroundStyle(Palette.muted)
                }
            }
        } else {
            Text("Loading the satellite calendar.").font(.clSecondary).foregroundStyle(Palette.muted)
        }
    }
}
