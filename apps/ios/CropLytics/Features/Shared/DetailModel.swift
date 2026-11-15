import Foundation
import Observation

/// The extra data behind "More detail" (machine-learning check, crop stress, standing water, insurance, glossary).
/// Loaded only when the section is opened, so the first screen stays quick on a slow connection.
@MainActor
@Observable
final class DetailModel {
    let field: FieldLocation
    private(set) var models: LoadState<ModelReport> = .idle
    private(set) var stress: LoadState<StressReport> = .idle
    private(set) var waterSeen: LoadState<WaterSeen> = .idle
    private(set) var insurance: LoadState<InsuranceProfile> = .idle
    private(set) var glossary: LoadState<Glossary> = .idle
    private let repository: any FieldRepository
    private var started = false

    init(field: FieldLocation, repository: any FieldRepository) {
        self.field = field
        self.repository = repository
    }

    func loadOnce() async {
        guard !started else { return }
        started = true
        models = .loading; stress = .loading; waterSeen = .loading; insurance = .loading; glossary = .loading
        await withTaskGroup(of: Void.self) { group in
            group.addTask { await self.loadModels() }
            group.addTask { await self.loadStress() }
            group.addTask { await self.loadWaterSeen() }
            group.addTask { await self.loadInsurance() }
            group.addTask { await self.loadGlossary() }
        }
    }

    // MARK: Plain-language lines

    /// Rule vs machine learning for spotting bare ground, as a comparison, not the answer.
    var mlLine: String? {
        guard let items = models.value?.items.filter({ $0.task == "bare_cover" && $0.id.contains("_year_v1") }), !items.isEmpty else { return nil }
        func acc(_ method: String) -> Int? {
            items.first { $0.method == method }?.metrics["accuracy"].map { Int(($0 * 100).rounded()) }
        }
        guard let rule = acc("rule_ndvi") else { return nil }
        var line = "The simple greenness rule matched the USDA crop map \(rule)% of the time in years it wasn't tuned on"
        let ml = [("random forest", acc("random_forest")), ("boosted trees", acc("hist_gbt"))].compactMap { n, v in v.map { "\(n) \($0)%" } }
        if !ml.isEmpty { line += "; the machine-learning models: \(ml.joined(separator: ", "))" }
        line += ". The app shows the rule's calendar; machine learning is a check beside it, not the answer."
        if rule < 80 { line += " The rule is below the 80% accuracy target here." }
        return line
    }

    static let driverWords = ["z_tmax": "unusual heat", "z_eto": "very thirsty air", "z_ndvi": "weaker growth than in its other years",
                              "iforest": "an unusual mix of heat, dryness and growth"]

    var stressLine: String? {
        guard let weeks = stress.value?.weeks, !weeks.isEmpty else { return nil }
        let flagged = weeks.filter { $0.flagZscore || $0.flagIforest }
        guard let lastYear = weeks.compactMap(\.isoYear).max() else { return nil }
        let thisYear = flagged.filter { $0.isoYear == lastYear }
        var why: [String: Int] = [:]
        thisYear.flatMap(\.drivers).forEach { why[$0, default: 0] += 1 }
        let top = why.max { $0.value < $1.value }?.key
        let years = Set(weeks.compactMap(\.isoYear))
        var line = "\(thisYear.count) crop-stress week\(thisYear.count == 1 ? "" : "s") in the \(lastYear) season"
        if let top { line += ", mostly \(Self.driverWords[top] ?? "unusual weather")" }
        line += ". \(flagged.count) flagged weeks across \(years.count) seasons checked."
        return line
    }

    var insuranceLine: String? {
        guard let p = insurance.value, let profile = p.profiles.values.max(by: { ($0.totalIndemnityUsd ?? 0) < ($1.totalIndemnityUsd ?? 0) }),
              let usd = profile.totalIndemnityUsd else { return nil }
        let money = usd >= 1e6 ? String(format: "$%.1f million", usd / 1e6) : "$\(Int((usd / 1000).rounded())) thousand"
        let span = (p.years.first.map(String.init) ?? "") + (p.years.count > 1 ? "–\(p.years.last!)" : "")
        return "\(money) paid out on \(profile.crop ?? "this crop") in \(profile.scope ?? "the county")\(span.isEmpty ? "" : ", \(span)"). County totals, not this farm."
    }

    private func loadModels() async { await consume(repository.models(field.id)) { self.models = $0 } }
    private func loadStress() async { await consume(repository.stress(field.id)) { self.stress = $0 } }
    private func loadWaterSeen() async { await consume(repository.waterSeen(field.id)) { self.waterSeen = $0 } }
    private func loadInsurance() async { await consume(repository.insurance(field.id)) { self.insurance = $0 } }
    private func loadGlossary() async { await consume(repository.glossary()) { self.glossary = $0 } }
}
