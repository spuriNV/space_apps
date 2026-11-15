import SwiftUI

/// The shared part of every "More detail": NASA data behind the field, the machine-learning check,
/// crop-stress weeks, standing water, crop insurance and words explained. Loads when opened.
struct FieldDetailSections: View {
    let field: FieldLocation
    @Environment(AppEnvironment.self) private var env
    @State private var model: DetailModel?

    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            NasaDataList(datasets: field.nasaDatasets)
            if let model {
                checks(model)
                glossary(model)
            } else {
                ProgressView().frame(maxWidth: .infinity)
            }
        }
        .task {
            let m = model ?? DetailModel(field: field, repository: env.repository)
            model = m
            await m.loadOnce()
        }
    }

    @ViewBuilder private func checks(_ model: DetailModel) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            SectionHeading(text: "Checks on the satellite readings")
            DetailLine(title: "Bare-ground detector: rule against machine learning",
                       state: model.models.isLoading ? .loading : model.mlLine.map(DetailLine.State.text) ?? .missing(model.models.error),
                       cite: "Bare-ground detectors from backend/ai, scored against the USDA Cropland Data Layer on held-out years.")
            DetailLine(title: "Crop-stress weeks",
                       state: model.stress.isLoading ? .loading : model.stressLine.map(DetailLine.State.text) ?? .missing(model.stress.error),
                       cite: "Two statistical methods (z-score and isolation forest) on satellite greenness and NASA POWER heat and dryness, growing season only.")
            DetailLine(title: "Standing water seen from space",
                       state: model.waterSeen.isLoading ? .loading : model.waterSeen.value?.summary.map(DetailLine.State.text) ?? .missing(model.waterSeen.error),
                       cite: "NASA/JPL OPERA surface water from HLS, 100 ft squares, clear images only.")
            DetailLine(title: "Crop insurance paid in the county",
                       state: model.insurance.isLoading ? .loading : model.insuranceLine.map(DetailLine.State.text) ?? .missing(model.insurance.error),
                       cite: "USDA Risk Management Agency cause-of-loss records.")
        }
    }

    @ViewBuilder private func glossary(_ model: DetailModel) -> some View {
        if let items = model.glossary.value?.items, !items.isEmpty {
            VStack(alignment: .leading, spacing: 10) {
                SectionHeading(text: "Words used here")
                ForEach(items.prefix(8)) { e in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(e.term).font(.clLabel).foregroundStyle(Palette.text)
                        Text(e.short).font(.clSecondary).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
                    }
                    .accessibilityElement(children: .combine)
                }
            }
        }
    }
}

/// One line in a detail block: loading, the plain sentence, or "not on the server yet".
struct DetailLine: View {
    enum State {
        case loading
        case text(String)
        case missing(AppError?)
    }
    let title: String
    let state: State
    let cite: String

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title).font(.clLabel).foregroundStyle(Palette.muted)
            switch state {
            case .loading:
                Text("Loading this check from the server").font(.clBody).redacted(reason: .placeholder)
            case .text(let t):
                Text(t).font(.clBody).foregroundStyle(Palette.text).fixedSize(horizontal: false, vertical: true)
                SourceLine(text: cite)
            case .missing(let error):
                Text(missingText(error))
                    .font(.clBody).foregroundStyle(Palette.muted).italic()
            }
        }
        .accessibilityElement(children: .combine)
    }

    private func missingText(_ error: AppError?) -> String {
        guard let error, error != .notFound else { return "Not on the server for this field yet." }
        return error.title + "."
    }
}

/// "NASA data behind this field": what each dataset tells the grower, its footprint in feet or miles, and whether it is live.
struct NasaDataList: View {
    let datasets: [NasaDataset]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            SectionHeading(text: "NASA data behind this field")
            if datasets.isEmpty {
                Text("Not on the server for this field yet.").font(.clBody).foregroundStyle(Palette.muted).italic()
            }
            ForEach(datasets) { d in
                VStack(alignment: .leading, spacing: 2) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(d.name).font(.clLabel).foregroundStyle(Palette.text)
                        Spacer(minLength: 8)
                        Text(statusWords(d.status))
                            .font(.clCite)
                            .italic(d.status != "live")
                            .foregroundStyle(d.status == "live" ? Palette.accent : Palette.warn)
                    }
                    if let t = d.tellsYou { Text(t).font(.clSecondary).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true) }
                    if let r = d.resolution {
                        Text("Footprint: \(Units.distanceInGrowerUnits(r))").font(.clCite).foregroundStyle(Palette.muted)
                    }
                    if let s = d.sourceURL, let url = URL(string: s) {
                        Link("Source", destination: url).font(.clCite)
                    }
                }
                .padding(.vertical, 2)
                .accessibilityElement(children: .combine)
                Hairline()
            }
        }
    }

    private func statusWords(_ s: String?) -> String {
        switch s {
        case "live": "Live"
        case "pending": "Still downloading"
        case "blocked": "Needs a login"
        default: s?.capitalized ?? "Unknown"
        }
    }
}
