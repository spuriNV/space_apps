import Foundation
import Observation
import SwiftUI
import UIKit

/// What goes on the one-page summary for the adviser (PLAN.md "Brief", fixed templates, no LLM).
struct SummaryContent: Sendable {
    let fieldName: String
    let subtitle: String
    let stateFieldNumber: String?
    let record: String
    let date: Date
    let now: [Answer]
    let season: [Answer]
    let today: RotationSummary?
    let alternative: AlternativeComparison?
    let limit: WaterLimitStore.Limit
    let checkLocally: [String]
}

@MainActor
@Observable
final class SummaryViewModel {
    let field: FieldLocation
    private(set) var nasaNow: LoadState<NasaNow> = .idle
    private(set) var calendar: LoadState<FieldCalendar> = .idle
    private(set) var strategies: LoadState<[Strategy]> = .idle
    private(set) var outlook: LoadState<Outlook> = .idle
    private(set) var pdfURL: URL?
    private(set) var pageImage: UIImage?
    private(set) var renderError: String?

    private let repository: any FieldRepository
    private let limits: WaterLimitStore
    private let today: Date

    init(field: FieldLocation, repository: any FieldRepository, limits: WaterLimitStore, today: Date) {
        self.field = field
        self.repository = repository
        self.limits = limits
        self.today = today
    }

    var isLoading: Bool { nasaNow.isLoading || strategies.isLoading || outlook.isLoading }
    var error: AppError? {
        guard let e = strategies.error, nasaNow.error != nil, outlook.error != nil else { return nil }
        return e
    }

    var content: SummaryContent {
        let limit = limits.limit(for: field.id)
        let now = FieldNowBuilder.build(.init(field: field, nasaNow: nasaNow.value, calendar: calendar.value,
                                              strategies: strategies.value, limit: limit, today: today))
        let season = outlook.value.map {
            ComingSeasonBuilder.build(outlook: $0, field: field, nasaNow: nasaNow.value, strategies: strategies.value, limit: limit)
        }
        let compare = strategies.value.flatMap { CompareBuilder.build(strategies: $0, calendar: calendar.value, limit: limit.value, count: 1) }
        let base = strategies.value?.first(where: \.isBaseline)
        let review = (base?.brief?.localReview ?? []).filter { $0.severity != "low" }.map { Self.plain($0.item) }.prefix(3)
        var check = Array(review)
        check.append("Your own water allocation, well records and soil test: the numbers here are regional.")
        return SummaryContent(
            fieldName: FieldNaming.displayName(field), subtitle: FieldNaming.subtitle(field), stateFieldNumber: field.dwrUniqueId,
            record: FieldNaming.recordLine(field), date: today, now: now.answers,
            season: season.map { [$0.rain, $0.water, $0.need] } ?? [],
            today: compare?.today, alternative: compare?.top.first, limit: limit, checkLocally: check
        )
    }

    /// Engine review notes without internal references ("(spec B11)", "(U)" = unverified).
    static func plain(_ item: String) -> String {
        item.replacingOccurrences(of: #"\s*\((spec [^)]*|U)\)"#, with: "", options: .regularExpression)
            .replacingOccurrences(of: " (U);", with: ";")
    }

    func load() async {
        if nasaNow.value == nil { nasaNow = .loading }
        if strategies.value == nil { strategies = .loading }
        if outlook.value == nil { outlook = .loading }
        await withTaskGroup(of: Void.self) { group in
            group.addTask { await self.loadNasaNow() }
            group.addTask { await self.loadCalendar() }
            group.addTask { await self.loadStrategies() }
            group.addTask { await self.loadOutlook() }
        }
    }

    /// Renders the page to a PDF file (US Letter) and a preview image, with ImageRenderer.
    func render(thumbnail: UIImage?) {
        let page = SummaryPage(content: content, thumbnail: thumbnail)
            .environment(\.colorScheme, .light)
            .environment(\.dynamicTypeSize, .large)
        let renderer = ImageRenderer(content: page)
        renderer.proposedSize = ProposedViewSize(width: SummaryPage.size.width, height: SummaryPage.size.height)
        renderer.scale = 2
        pageImage = renderer.uiImage

        let safeName = content.fieldName.replacingOccurrences(of: "[^A-Za-z0-9]+", with: "-", options: .regularExpression)
        let url = FileManager.default.temporaryDirectory.appending(path: "CropLytics-\(safeName).pdf")
        var box = CGRect(origin: .zero, size: SummaryPage.size)
        var ok = false
        renderer.render { _, draw in
            guard let pdf = CGContext(url as CFURL, mediaBox: &box, [
                kCGPDFContextTitle as String: "Field summary: \(content.fieldName)",
                kCGPDFContextCreator as String: "CropLytics",
            ] as CFDictionary) else { return }
            pdf.beginPDFPage(nil)
            draw(pdf)
            pdf.endPDFPage()
            pdf.closePDF()
            ok = true
        }
        if ok { pdfURL = url; renderError = nil } else { renderError = "Couldn't make the PDF on this phone." }
    }

    private func loadNasaNow() async { await consume(repository.nasaNow(field.id)) { self.nasaNow = $0 } }
    private func loadCalendar() async { await consume(repository.calendar(field.id)) { self.calendar = $0 } }
    private func loadStrategies() async { await consume(repository.strategies(field.id)) { self.strategies = $0 } }
    private func loadOutlook() async { await consume(repository.outlook(field.id)) { self.outlook = $0 } }
}
