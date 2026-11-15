import SwiftUI
import UIKit

/// What goes on the one-page summary for the adviser (PLAN.md "Brief": fixed templates, no LLM).
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

enum SummaryBuilder {
    /// Engine review notes without internal references ("(spec B11)", "(U)" = unverified).
    static func plain(_ item: String) -> String {
        item.replacingOccurrences(of: #"\s*\((spec [^)]*|U)\)"#, with: "", options: .regularExpression)
    }

    @MainActor
    static func content(session: FieldSession, limit: WaterLimitStore.Limit, today: TimePoint, pick: String?) -> SummaryContent {
        let f = session.field
        let strategies = session.currentStrategies
        let now = FieldNowBuilder.build(.init(field: f, nasaNow: session.nasaNow.value, calendar: session.calendar.value, strategies: strategies,
                                              limit: limit, t: today, today: today, daily: session.daily.value))
        let season = session.outlook.value.map { ComingSeasonBuilder.build(outlook: $0, field: f, nasaNow: session.nasaNow.value, strategies: strategies, limit: limit) }
        let all = strategies.flatMap { CompareBuilder.build(strategies: $0, calendar: session.calendar.value, limit: limit.value, count: 10) }
        let alt = all?.top.first { $0.id == pick } ?? all?.top.first
        let review = (strategies?.first(where: \.isBaseline)?.brief?.localReview ?? []).filter { $0.severity != "low" }.map { plain($0.item) }.prefix(3)
        var check = Array(review)
        check.append(f.isBC ? "The water licence, the fish-flow orders in force, and a soil test: the numbers here are regional."
                            : "Your own water allocation, well records and soil test: the numbers here are regional.")
        return SummaryContent(fieldName: FieldNaming.displayName(f), subtitle: FieldNaming.subtitle(f), stateFieldNumber: f.isBC ? nil : f.dwrUniqueId,
                              record: FieldNaming.recordLine(f), date: today.date,
                              now: now.answers.filter { !$0.detailOnly }.prefix(4).map { $0 },
                              season: season.map { [$0.rain, $0.water, $0.need] } ?? [],
                              today: all?.today, alternative: alt, limit: limit, checkLocally: check)
    }
}

/// "Print for your adviser": pick the option to talk about, preview the page, then share or print the PDF.
struct PrintPanel: View {
    let session: FieldSession
    @Environment(AppModel.self) private var app
    @Environment(AppEnvironment.self) private var env
    @State private var pick: String?
    @State private var image: UIImage?
    @State private var pdf: URL?
    @State private var failed = false

    var body: some View {
        let limit = env.limits.limit(for: session.field.id)
        let options = session.currentStrategies.flatMap { CompareBuilder.build(strategies: $0, calendar: session.calendar.value, limit: limit.value, count: 10)?.top } ?? []
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader("Print for your adviser")
            Text("One page: what this field is, what's likely this season, the option to talk about, and what to check locally.")
                .font(.clBody).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
            if !options.isEmpty {
                Text("The option to talk about").font(.clLabel).foregroundStyle(Palette.muted)
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(options) { o in
                            FilterChip(title: o.option.name, isOn: (pick ?? options.first?.id) == o.id) { pick = o.id }
                        }
                    }
                }
                .accessibilityIdentifier("print-pick")
            }
            if let image, !session.isLoadingCore {
                Image(uiImage: image).resizable().aspectRatio(SummaryPage.size, contentMode: .fit)
                    .clipShape(RoundedRectangle(cornerRadius: Radius.sm, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: Radius.sm, style: .continuous).strokeBorder(Palette.line))
                    .elevation2()
                    .accessibilityLabel("Summary page for \(FieldNaming.displayName(session.field))")
                    .accessibilityIdentifier("summary-page")
                if let pdf {
                    HStack(spacing: 8) {
                        ShareLink(item: pdf, subject: Text("Field summary: \(FieldNaming.displayName(session.field))"),
                                  preview: SharePreview("Field summary", image: Image(uiImage: image))) {
                            Label("Share PDF", systemImage: "square.and.arrow.up")
                        }
                        .buttonStyle(.pill(.primary, fullWidth: true))
                        .accessibilityIdentifier("share-pdf")
                        Button { printPDF(pdf) } label: { Label("Print", systemImage: "printer") }
                            .buttonStyle(.pill(.outline))
                            .accessibilityIdentifier("print-pdf")
                    }
                }
                SourceLine(text: "US Letter PDF. Numbers are today's, with the water limit you set on Compare.")
            } else if failed {
                Text("Couldn't make the PDF on this phone.").font(.clBody).foregroundStyle(Palette.bad)
            } else {
                RoundedRectangle(cornerRadius: Radius.sm).fill(Palette.panel2).aspectRatio(SummaryPage.size, contentMode: .fit)
                    .overlay(ProgressView("Making the page").font(.clBody))
            }
        }
        .task(id: renderKey(limit)) {
            await env.thumbnails.load(session.field, size: CGSize(width: 132, height: 90))
            render(limit: limit)
        }
    }

    private func renderKey(_ limit: WaterLimitStore.Limit) -> String {
        "\(pick ?? "-")|\(limit.value)|\(session.isLoadingCore)|\(session.currentStrategies?.count ?? 0)|\(session.outlook.value != nil)"
    }

    private func render(limit: WaterLimitStore.Limit) {
        let content = SummaryBuilder.content(session: session, limit: limit, today: app.today, pick: pick)
        let page = SummaryPage(content: content, thumbnail: env.thumbnails.image(for: session.field.id))
        image = PDFRenderer.image(page)
        pdf = PDFRenderer.pdf(page, name: content.fieldName)
        failed = pdf == nil
    }

    private func printPDF(_ url: URL) {
        let c = UIPrintInteractionController.shared
        let info = UIPrintInfo(dictionary: nil)
        info.outputType = .general
        info.jobName = "Field summary"
        c.printInfo = info
        c.printingItem = url
        c.present(animated: true)
    }
}

/// ImageRenderer to a preview image and a one-page US Letter PDF.
@MainActor
enum PDFRenderer {
    static func image(_ page: SummaryPage) -> UIImage? {
        let r = ImageRenderer(content: page.environment(\.colorScheme, .light).environment(\.dynamicTypeSize, .large))
        r.proposedSize = ProposedViewSize(SummaryPage.size)
        r.scale = 2
        return r.uiImage
    }

    static func pdf(_ page: SummaryPage, name: String) -> URL? {
        let r = ImageRenderer(content: page.environment(\.colorScheme, .light).environment(\.dynamicTypeSize, .large))
        r.proposedSize = ProposedViewSize(SummaryPage.size)
        let safe = name.replacingOccurrences(of: "[^A-Za-z0-9]+", with: "-", options: .regularExpression)
        let url = FileManager.default.temporaryDirectory.appending(path: "CropLytics-\(safe).pdf")
        var box = CGRect(origin: .zero, size: SummaryPage.size)
        var ok = false
        r.render { _, draw in
            guard let ctx = CGContext(url as CFURL, mediaBox: &box, [kCGPDFContextTitle as String: "Field summary: \(name)", kCGPDFContextCreator as String: "CropLytics"] as CFDictionary) else { return }
            ctx.beginPDFPage(nil); draw(ctx); ctx.endPDFPage(); ctx.closePDF()
            ok = true
        }
        return ok ? url : nil
    }
}
