import SwiftUI

/// "Your field now": what the field is, a compact visual summary, then at most 4 plain answers.
struct FieldNowScreen: View {
    let field: FieldLocation
    @Environment(AppEnvironment.self) private var env
    @State private var model: FieldNowViewModel?

    var body: some View {
        Group {
            if let model { FieldNowContent(model: model) } else { Color.clear }
        }
        .task(id: field.id) {
            let m = FieldNowViewModel(field: field, repository: env.repository, limits: env.limits, today: env.today())
            model = m
            await m.load()
        }
    }
}

private struct FieldNowContent: View {
    let model: FieldNowViewModel
    @Environment(AppModel.self) private var app

    var body: some View {
        ScrollView {
            if let error = model.blockingError {
                ErrorStateView(error: error) { Task { await model.load() } }
            } else {
                let p = model.presentation
                VStack(alignment: .leading, spacing: 18) {
                    FieldHeader(field: model.field)
                    FieldMap(field: model.field)
                    SummaryPanel(summary: p.summary)
                        .placeholder(model.isLoading)
                    VStack(alignment: .leading, spacing: 14) {
                        ForEach(p.answers) { a in
                            AnswerView(answer: a)
                            if a.id != p.answers.last?.id { Hairline() }
                        }
                    }
                    .placeholder(model.isLoading)
                    SavedNote(freshness: model.freshness)
                    NextSteps()
                    MoreDetail {
                        AboutField(field: model.field, calendar: model.calendar.value)
                        CropRecord(field: model.field)
                        FieldDetailSections(field: model.field)
                    }
                }
                .padding(Metrics.gutter)
            }
        }
        .background(Palette.paper)
        .refreshable { await model.load() }
    }
}

/// The glance block: season strip, rain vs normal, water need vs limit, greenness, soil and groundwater.
private struct SummaryPanel: View {
    let summary: FieldNowPresentation.Summary

    var body: some View {
        Panel {
            SectionHeading(text: "Your field now")
            VStack(alignment: .leading, spacing: 4) {
                Text("\(String(summary.stripYear)) so far").font(.clSecondary).foregroundStyle(Palette.muted)
                SeasonStripView(classes: summary.strip, marker: summary.todayDekad)
                StripMonths()
                Text(summary.stage)
                    .font(.clAnswer)
                    .foregroundStyle(Palette.text)
                    .accessibilityLabel("On the field now: \(summary.stage)")
            }
            Grid(alignment: .topLeading, horizontalSpacing: 16, verticalSpacing: 14) {
                GridRow {
                    meter(summary.rain, fallback: "Rain since 1 Oct")
                    meter(summary.water, fallback: "Water need, a year")
                }
                GridRow {
                    meter(summary.greenness, fallback: "Greenness")
                    Color.clear.gridCellUnsizedAxes([.horizontal, .vertical])
                }
            }
            PercentileTrack(soil: summary.soilPercentile, groundwater: summary.groundwaterPercentile, note: summary.soilGroundwaterNote)
            StripKey()
        }
        .accessibilityIdentifier("field-summary")
    }

    @ViewBuilder private func meter(_ m: Meter?, fallback: String) -> some View {
        if let m {
            MeterView(meter: m).frame(maxWidth: .infinity, alignment: .leading)
        } else {
            VStack(alignment: .leading, spacing: 4) {
                Text(fallback).font(.clSecondary).foregroundStyle(Palette.muted)
                Text("Not available").font(.clBody).foregroundStyle(Palette.muted).italic()
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

/// What you can do next, in the grower's words. One primary action: the summary for the adviser.
private struct NextSteps: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        VStack(spacing: 8) {
            step("What's likely this winter", "Rain, water supply, next season's need", .season)
            step("Compare other rotations", "What you'd gain and give up", .compare)
            Button {
                app.tab = .summary
            } label: {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Summary for your adviser").font(.clBodyStrong)
                        Text("One page, ready to share").font(.clCite).opacity(0.9)
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                }
                .padding(12)
                .frame(maxWidth: .infinity)
                .foregroundStyle(Palette.accentInk)
                .background(Palette.accent, in: RoundedRectangle(cornerRadius: Metrics.radius))
            }
            .accessibilityIdentifier("go-summary")
        }
    }

    private func step(_ title: String, _ sub: String, _ tab: AppTab) -> some View {
        Button { app.tab = tab } label: {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(title).font(.clBodyStrong).foregroundStyle(Palette.text)
                    Text(sub).font(.clCite).foregroundStyle(Palette.muted)
                }
                Spacer()
                Image(systemName: "chevron.right").foregroundStyle(Palette.muted)
            }
            .padding(12)
            .overlay(RoundedRectangle(cornerRadius: Metrics.radius).strokeBorder(Palette.line))
        }
        .buttonStyle(.plain)
    }
}

/// About the field: soil, water, salt, slope, when it is usually bare.
struct AboutField: View {
    let field: FieldLocation
    let calendar: FieldCalendar?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            SectionHeading(text: "About this field")
            if let s = field.soil {
                FactRow(label: "Soil", value: [s.muname?.components(separatedBy: ",").first, s.textureClass?.lowercased()].compactMap { $0 }.joined(separator: ", "),
                        note: "USDA soil survey (SSURGO).")
                if let awc = s.awcMmPerM?.value {
                    let inFt = awc / 1000 * 12
                    FactRow(label: "Holds", value: "\(Units.oneDecimal(inFt)) in of water per foot of soil" + (inFt < 1.4 ? " (low: needs frequent, short irrigations)" : inFt > 2 ? " (high)" : ""))
                }
                if let d = s.drainageClass {
                    FactRow(label: "Drainage", value: d + (s.hydrologicGroup.map { "; runoff group \($0)" } ?? ""))
                }
                if let ec = s.ecDsPerM {
                    FactRow(label: "Salt", value: ec >= 4 ? "Salty soil; limits salt-sensitive crops" : "Low salt", note: String(format: "EC %.1f dS/m", ec), warn: ec >= 4)
                }
            }
            if let w = field.water {
                FactRow(label: "Water", value: (w.isSurface ? "Surface water" : "Groundwater (wells)") + (w.district.map { ", \($0.replacingOccurrences(of: " (U)", with: ""))" } ?? ""))
            }
            if let slope = field.terrain?.slopeMeanPct?.value {
                let words = slope < 2 ? "Nearly flat" : slope < 5 ? "Gentle slope" : "Sloping"
                let low = field.terrain?.lowSpotFraction?.value.map { "; low spots on about \(Int(($0 * 100).rounded()))% of the field, where water ponds and frost settles" } ?? ""
                FactRow(label: "Slope", value: "\(words), about \(Units.oneDecimal(slope))% on average\(low).",
                        note: "NASA NASADEM elevation, 100 ft squares; radar reads 1 to 2% even on a levelled field.")
            }
            if let bare = calendar?.observedBareDays() {
                FactRow(label: "Usually bare", value: "About \(bare.days) days a year",
                        note: "Seen by satellite, \(bare.years.map(String.init).joined(separator: ", ")). \(bareDefinition)")
            }
        }
    }
}

/// Crops grown, one coloured square per year (USDA Cropland Data Layer).
struct CropRecord: View {
    let field: FieldLocation

    var body: some View {
        let years = FieldNaming.sortedYears(field.cropHistory).filter { $0 >= 2016 }
        VStack(alignment: .leading, spacing: 8) {
            SectionHeading(text: "Crops grown here")
            Text(FieldNaming.recordLine(field)).font(.clBody).foregroundStyle(Palette.text2)
            HStack(spacing: 3) {
                ForEach(years, id: \.self) { y in
                    let crop = FieldNaming.cropName(field.cropHistory[String(y)])
                    VStack(spacing: 2) {
                        Rectangle().fill(DataColor.crop(crop)).frame(height: 14)
                        Text("'\(String(y).suffix(2))").font(.clCite).foregroundStyle(Palette.muted).minimumScaleFactor(0.7).lineLimit(1)
                    }
                    .accessibilityElement()
                    .accessibilityLabel("\(y): \(crop)")
                }
            }
            FlowLayout(spacing: 10) {
                ForEach(Array(Set(years.map { FieldNaming.cropName(field.cropHistory[String($0)]) })).sorted(), id: \.self) { c in
                    HStack(spacing: 4) {
                        Rectangle().fill(DataColor.crop(c)).frame(width: 10, height: 10)
                        Text(c).font(.clCite).foregroundStyle(Palette.muted)
                    }
                }
            }
            .accessibilityHidden(true)
            SourceLine(text: "USDA Cropland Data Layer, one crop per year.")
        }
    }
}
