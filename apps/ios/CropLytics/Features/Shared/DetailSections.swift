import SwiftUI

/// Plain-language lines for the adviser detail.
enum DetailLines {
    /// Rule vs machine learning for spotting bare ground, as a comparison, not the answer.
    static func ml(_ models: ModelReport?) -> String? {
        guard let items = models?.items.filter({ $0.task == "bare_cover" && $0.id.contains("_year_v1") }), !items.isEmpty else { return nil }
        func acc(_ m: String) -> Int? { items.first { $0.method == m }?.metrics["accuracy"].map { Int(($0 * 100).rounded()) } }
        guard let rule = acc("rule_ndvi") else { return nil }
        var line = "The simple greenness rule matched the crop map \(rule)% of the time in years it wasn't tuned on"
        let ml = [("random forest", acc("random_forest")), ("boosted trees", acc("hist_gbt"))].compactMap { n, v in v.map { "\(n) \($0)%" } }
        if !ml.isEmpty { line += "; the machine-learning models: \(ml.joined(separator: ", "))" }
        return line + ". The app shows the rule's calendar; machine learning is a check beside it, not the answer."
    }

    static func insurance(_ p: InsuranceProfile) -> String? {
        guard let profile = p.profiles.values.max(by: { ($0.totalIndemnityUsd ?? 0) < ($1.totalIndemnityUsd ?? 0) }), let usd = profile.totalIndemnityUsd, usd > 0 else { return nil }
        let money = usd >= 1e6 ? String(format: "$%.1f million", usd / 1e6) : "$\(Int((usd / 1000).rounded())) thousand"
        let span = (p.years.first.map(String.init) ?? "") + (p.years.count > 1 ? "–\(p.years.last!)" : "")
        return "\(money) paid out on \(profile.crop ?? "this crop") in \(profile.scope ?? "the county")\(span.isEmpty ? "" : ", \(span)")."
    }
}

/// Checks on the satellite readings (rule vs ML, BC data gaps), shown with More detail.
struct DetailChecks: View {
    let session: FieldSession
    var body: some View {
        let f = session.field
        VStack(alignment: .leading, spacing: 10) {
            SectionHeader("Checks on the readings")
            DetailLine(title: "Bare-ground detector: rule against machine learning",
                       state: session.models.isLoading ? .loading : DetailLines.ml(session.models.value).map(DetailLine.State.text) ?? .missing(session.models.error, f.gap("ml_calendar")?.reason),
                       cite: "Detectors scored against the crop map on held-out years.")
            if f.isBC, !f.dataGaps.isEmpty {
                SectionHeader("Not available in British Columbia").padding(.top, 12)
                ForEach(f.dataGaps) { g in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(g.what ?? g.id).font(.clLabel).foregroundStyle(Palette.text)
                        if let r = g.reason { Text(r).font(.clSecondary).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true) }
                    }
                    .padding(.vertical, 4)
                    .accessibilityElement(children: .combine)
                }
            }
        }
    }
}

/// One detail line: loading, the plain sentence, or "not on the server yet".
struct DetailLine: View {
    enum State {
        case loading
        case text(String)
        case missing(AppError?, String?)
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
            case .missing(let error, let reason):
                Text(reason.map { "Not available here. \($0)" } ?? (error == nil || error == .notFound ? "Not ready for this field yet." : error!.title + "."))
                    .font(.clBody).italic().foregroundStyle(Palette.muted).fixedSize(horizontal: false, vertical: true)
            }
        }
        .accessibilityElement(children: .combine)
    }
}

/// "NASA data behind this field": what each dataset tells the grower, its footprint in feet or miles, and whether it is live.
struct NasaDataList: View {
    let datasets: [NasaDataset]

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            if datasets.isEmpty {
                Text("Not on the server for this field yet.").font(.clBody).italic().foregroundStyle(Palette.muted)
            }
            ForEach(Array(datasets.enumerated()), id: \.element.id) { i, d in
                if i > 0 { Hairline() }
                VStack(alignment: .leading, spacing: 3) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(d.name).font(.clLabel).foregroundStyle(Palette.text)
                        Spacer(minLength: 8)
                        if d.status == "live" {
                            Text("Live").font(.clCite).foregroundStyle(Palette.accent)
                        } else if d.status == "estimate" {
                            StatusWord(kind: .estimate)
                        } else {
                            Text(d.status == "pending" ? "Still downloading" : d.status == "blocked" ? "Needs a login" : (d.status ?? "").capitalized)
                                .font(.clCite).italic().foregroundStyle(Palette.warn)
                        }
                    }
                    if let t = d.tellsYou { Text(t).font(.clSecondary).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true) }
                    if let r = d.resolution { Text("Footprint: \(Units.distanceInGrowerUnits(r))").font(.clCite).foregroundStyle(Palette.muted) }
                    if let s = d.sourceURL, let url = URL(string: s), url.scheme?.hasPrefix("http") == true {
                        Link("Source", destination: url).font(.clCite)
                    }
                }
                .padding(.vertical, 10)
                .accessibilityElement(children: .combine)
            }
        }
    }
}
