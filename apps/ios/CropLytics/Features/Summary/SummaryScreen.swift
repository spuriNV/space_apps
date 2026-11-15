import SwiftUI

/// "Summary for your adviser": one page, previewed as it will print, shared as a PDF.
struct SummaryScreen: View {
    let field: FieldLocation
    @Environment(AppEnvironment.self) private var env
    @State private var model: SummaryViewModel?

    var body: some View {
        Group {
            if let model { SummaryContentView(model: model) } else { Color.clear }
        }
        .task(id: field.id) {
            let m = SummaryViewModel(field: field, repository: env.repository, limits: env.limits, today: env.today())
            model = m
            await env.thumbnails.load(field, size: CGSize(width: 208, height: 140))
            await m.load()
            m.render(thumbnail: env.thumbnails.image(for: field.id))
        }
    }
}

private struct SummaryContentView: View {
    let model: SummaryViewModel
    @Environment(AppEnvironment.self) private var env

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("One page with what this field is, what's likely this season, the option to talk about, and what to check locally. Share it as a PDF or print it.")
                    .font(.clBody).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
                if let error = model.error {
                    ErrorStateView(error: error) { Task { await model.load(); model.render(thumbnail: env.thumbnails.image(for: model.field.id)) } }
                } else if let image = model.pageImage, !model.isLoading {
                    Image(uiImage: image)
                        .resizable()
                        .aspectRatio(SummaryPage.size, contentMode: .fit)
                        .overlay(Rectangle().strokeBorder(Palette.line))
                        .shadow(color: .black.opacity(0.18), radius: 3, y: 1)
                        .accessibilityLabel("Summary page for \(model.content.fieldName)")
                        .accessibilityIdentifier("summary-page")
                    if let url = model.pdfURL {
                        ShareLink(item: url, subject: Text("Field summary: \(model.content.fieldName)"),
                                  message: Text("Field summary from CropLytics"),
                                  preview: SharePreview("Field summary: \(model.content.fieldName)", image: Image(uiImage: image))) {
                            Label("Share with your adviser", systemImage: "square.and.arrow.up")
                                .font(.clBodyStrong)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 6)
                        }
                        .buttonStyle(.borderedProminent)
                        .accessibilityIdentifier("share-pdf")
                    }
                    if let e = model.renderError { Text(e).font(.clCite).foregroundStyle(Palette.bad) }
                    SourceLine(text: "US Letter PDF. Numbers are the same as on the other tabs, with the water limit you set on Compare.")
                } else {
                    Rectangle().fill(Palette.panel2).aspectRatio(SummaryPage.size, contentMode: .fit)
                        .overlay(ProgressView("Making the page").font(.clBody))
                        .accessibilityLabel("Making the summary page")
                }
            }
            .padding(Metrics.gutter)
        }
        .background(Palette.paper)
        .toolbar {
            if let url = model.pdfURL {
                ToolbarItem(placement: .topBarLeading) {
                    ShareLink(item: url) { Label("Share PDF", systemImage: "square.and.arrow.up") }
                }
            }
        }
        .refreshable {
            await model.load()
            model.render(thumbnail: env.thumbnails.image(for: model.field.id))
        }
    }
}
