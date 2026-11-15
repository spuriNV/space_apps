import Foundation
import CoreGraphics
import Testing
@testable import CropLytics

@Suite("View models")
@MainActor
struct ViewModelTests {
    private func fields() async -> (AppModel, [FieldLocation]) {
        let app = AppModel(repository: TestAPI.fixtureRepository(), defaults: UserDefaults(suiteName: UUID().uuidString)!)
        await app.loadFields()
        return (app, app.fields.value ?? [])
    }

    @Test("Field list: farmer names, search by town, county or crop, open goes to Field now")
    func fieldsList() async throws {
        let (app, all) = await fields()
        #expect(all.count == 2)
        let model = FieldsViewModel(app: app)
        #expect(model.rows.map(\.name).contains("Rice field 3.5 miles east of Williams"))
        model.searchText = "kings"
        #expect(model.rows.map(\.id) == ["caf_tulare_forage"])
        model.searchText = "rice WILLIAMS"
        #expect(model.rows.map(\.id) == ["car_colusa_rice"])
        model.searchText = "almonds"
        #expect(model.rows.isEmpty)
        model.open("car_colusa_rice")
        #expect(app.tab == .now)
        #expect(app.selectedField?.id == "car_colusa_rice")
    }

    @Test("Field now: a summary and at most 4 answers, with the example limit flagged")
    func fieldNow() async throws {
        let (_, all) = await fields()
        let colusa = try #require(all.first { $0.id == "car_colusa_rice" })
        let model = FieldNowViewModel(field: colusa, repository: TestAPI.fixtureRepository(), limits: TestAPI.limits(), today: TestAPI.today)
        await model.load()
        #expect(!model.isLoading)
        let p = model.presentation
        #expect(p.answers.count == 4)
        #expect(p.answers.map(\.id) == ["growing", "rain", "water", "soil"])
        let rain = try #require(p.answers.first { $0.id == "rain" })
        #expect(rain.headline == "So far drier than normal")
        #expect(rain.detail.hasPrefix("1.9 inches since 1 Oct"))
        let water = try #require(p.answers.first { $0.id == "water" })
        #expect(water.headline == "Short by about 0.2 acre-feet per acre")
        #expect(water.detail.contains("example"))
        #expect(p.summary.rain?.note.hasPrefix("62% of normal") == true)
        #expect(p.summary.water?.warn == true)
        #expect(p.summary.groundwaterPercentile == 52.7)
        #expect(p.summary.strip.count == 36)
        #expect(model.freshness == nil)
    }

    @Test("Coming season: three items; rain outlook, water supply and next season's need")
    func comingSeason() async throws {
        let (_, all) = await fields()
        let kings = try #require(all.first { $0.id == "caf_tulare_forage" })
        let model = ComingSeasonViewModel(field: kings, repository: TestAPI.fixtureRepository(), limits: TestAPI.limits())
        await model.load()
        let p = try #require(model.presentation)
        #expect(p.rain.headline == "NOAA's outlook leans wetter than normal this winter")
        #expect(p.water.headline.hasPrefix("Groundwater under this basin is far below usual"))
        #expect(p.need.headline.contains("over your limit"))
        #expect(p.needBars.count == 4)
    }

    @Test("Compare: today vs top 2; the water limit is saved per field and re-scored")
    func compare() async throws {
        let (_, all) = await fields()
        let colusa = try #require(all.first { $0.id == "car_colusa_rice" })
        let limits = TestAPI.limits()
        let model = CompareViewModel(field: colusa, repository: TestAPI.fixtureRepository(), limits: limits, debounce: .milliseconds(10))
        await model.load()
        let p = try #require(model.presentation)
        #expect(p.today.id == "car0_rice_winterflood")
        #expect(p.top.count == 2)
        #expect(p.top.first?.id == "car2_dryyear_safflower")
        let safflower = try #require(p.top.first)
        #expect(safflower.gains.first?.title == "Needs less irrigation water")
        #expect(safflower.gains.first?.delta.hasPrefix("about 3.3 acre-ft/acre less a year") == true)
        #expect(safflower.losses.contains { $0.id == "bare" })
        #expect(p.all.count == 4)

        #expect(model.limit == .init(value: 5.0, isExample: true))
        model.setLimit(3.04)
        #expect(limits.limit(for: "car_colusa_rice") == .init(value: 3.0, isExample: false))
        #expect(limits.limit(for: "caf_tulare_forage").isExample)
        await model.pendingRescore?.value
        #expect(model.scoredLimit == 3.0)
        #expect(model.presentation?.today.fit == .over)
        model.resetLimit()
        #expect(model.limit.isExample)
    }

    @Test("Summary: renders a one-page US Letter PDF")
    func summaryPDF() async throws {
        let (_, all) = await fields()
        let colusa = try #require(all.first { $0.id == "car_colusa_rice" })
        let model = SummaryViewModel(field: colusa, repository: TestAPI.fixtureRepository(), limits: TestAPI.limits(), today: TestAPI.today)
        await model.load()
        let content = model.content
        #expect(content.now.count == 4)
        #expect(content.season.count == 3)
        #expect(content.alternative != nil)
        model.render(thumbnail: nil)
        let url = try #require(model.pdfURL)
        let pdf = try #require(CGPDFDocument(url as CFURL))
        #expect(pdf.numberOfPages == 1)
        let box = try #require(pdf.page(at: 1)?.getBoxRect(.mediaBox))
        #expect(box.size == CGSize(width: 612, height: 792))
    }
}
