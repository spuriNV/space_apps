import Foundation
import CoreGraphics
import Testing
@testable import CropLytics

@Suite("App model, field session and screens")
@MainActor
struct ViewModelTests {
    private func app(limits: WaterLimitStore? = nil) async -> AppModel {
        let m = AppModel(repository: TestAPI.fixtureRepository(), defaults: UserDefaults(suiteName: UUID().uuidString)!,
                         today: TestAPI.today, limits: limits)
        await m.loadFields()
        return m
    }

    private func session(_ id: String) async throws -> (AppModel, FieldSession) {
        let a = await app()
        a.open(id)
        let s = try #require(a.session)
        await s.load()
        return (a, s)
    }

    @Test("Fields load; opening one shares its data across tabs; home closes it")
    func appModel() async throws {
        let limits = TestAPI.limits()
        let a = await app(limits: limits)
        #expect(a.fields.value?.count == 11)
        #expect(a.pickerOpen)
        #expect(limits.limit(for: "car_glenn_rice") == .init(value: 5.0, isExample: true))
        a.open("car_colusa_rice")
        #expect(a.selectedField?.id == "car_colusa_rice")
        #expect(!a.pickerOpen && a.detent == .half && a.tab == .now)
        let first = a.session
        a.select(tab: .compare)
        #expect(a.tab == .compare && a.session === first)
        a.showPicker()
        #expect(a.pickerOpen && a.selectedField != nil)
        a.goHome()
        #expect(a.session == nil && a.pickerOpen)
        a.select(tab: .year)
        #expect(a.pickerOpen, "No field yet: the tabs send the grower to the pick list")
    }

    @Test("Date control and replay stay within today")
    func dateAndReplay() async throws {
        let a = await app()
        a.setDate(TimePoint(year: 2023, dekad: 7))
        #expect(!a.isToday && a.t.label == "mid Mar 2023")
        a.setDate(a.today.advanced(by: 10))
        #expect(a.t == a.today)
        a.toggleReplay()
        #expect(a.playing && a.t == TimePoint(year: 2023, dekad: 0))
        try await Task.sleep(for: .milliseconds(500))
        #expect(a.t > TimePoint(year: 2023, dekad: 0))
        a.backToToday()
        #expect(!a.playing && a.isToday)
    }

    @Test("Pick list search and Rice / Forage / BC chips")
    func picker() async throws {
        let loaded = await app()
        let fields = try #require(loaded.fields.value)
        #expect(PickerPanel.filter(fields, query: "", family: "rice").count == 6)
        #expect(PickerPanel.filter(fields, query: "", family: "bc").map(\.id) == ["bc_salmon_river_forage"])
        #expect(PickerPanel.filter(fields, query: "", family: "forage").allSatisfy { !$0.isBC && $0.family == "forage" })
        #expect(PickerPanel.filter(fields, query: "williams", family: nil).map(\.id) == ["car_colusa_rice"])
        #expect(PickerPanel.filter(fields, query: "british columbia", family: nil).count == 1)
        #expect(PickerPanel.filter(fields, query: "almonds", family: nil).isEmpty)
        let bc = fields.first(where: \.isBC)!
        #expect(FieldNaming.place(bc) == "Columbia-Shuswap, BC")
        #expect(FieldNaming.notable(bc).hasPrefix("Irrigation stopped by a fish-flow order in Aug 2023"))
        #expect(FieldNaming.notable(fields[0]).hasPrefix("Left fallow in the 2022 drought"))
    }

    @Test("Field now today: summary, farmer answers, soil answer, example limit; detail answers flagged")
    func fieldNowToday() async throws {
        let (a, s) = try await session("car_colusa_rice")
        let p = FieldNowBuilder.build(.init(field: s.field, nasaNow: s.nasaNow.value, calendar: s.calendar.value, strategies: s.currentStrategies,
                                            limit: TestAPI.limits().limit(for: s.field.id), t: a.t, today: a.today, daily: s.daily.value,
                                            stress: s.stress.value, waterSeen: s.waterSeen.value))
        #expect(p.heading == "Your field now")
        let farmer = p.answers.filter { !$0.detailOnly }.map(\.id)
        #expect(farmer == ["growing", "rain", "water", "soil", "soil-kind"])
        #expect(p.answers.filter(\.detailOnly).map(\.id).contains("heat"))
        let rain = try #require(p.answers.first { $0.id == "rain" })
        #expect(rain.headline == "So far drier than normal")
        let water = try #require(p.answers.first { $0.id == "water" })
        #expect(water.headline == "Short by about 0.2 acre-feet per acre")
        #expect(water.status?.kind == .example)
        #expect(p.answers.first { $0.id == "soil-kind" }?.headline == "Clay loam")
        #expect(p.summary.groundwaterPercentile == 52.7)
        #expect(p.summary.strip.count == 36 && p.summary.marker == 31)
    }

    @Test("Field now on a past date reads the daily record")
    func fieldNowPast() async throws {
        let (_, s) = try await session("car_colusa_rice")
        let t = TimePoint(year: 2023, dekad: 7)
        let p = FieldNowBuilder.build(.init(field: s.field, nasaNow: s.nasaNow.value, calendar: s.calendar.value, strategies: s.currentStrategies,
                                            limit: .init(value: 5, isExample: true), t: t, today: TestAPI.todayPoint, daily: s.daily.value))
        #expect(p.heading == "Your field in mid Mar 2023")
        let rain = try #require(p.answers.first { $0.id == "rain" })
        #expect(rain.headline.hasPrefix("So far"))
        #expect(rain.detail.contains("since 1 Oct"))
        #expect(p.summary.stripYear == 2023)
    }

    @Test("BC field: water orders, rain-fed option, First Nations")
    func bcField() async throws {
        let (_, s) = try await session("bc_salmon_river_forage")
        #expect(s.firstNations.value?.lowerRiver?.nation == "Splatsin")
        #expect(s.salmon.error == .notFound, "The salmon route isn't published, so the panel stays hidden")
        let o = try #require(s.outlook.value)
        let season = ComingSeasonBuilder.build(outlook: o, field: s.field, nasaNow: s.nasaNow.value, strategies: s.currentStrategies,
                                               limit: .init(value: 3, isExample: true))
        #expect(season.water.headline.contains("order to stop irrigating"))
        let compare = try #require(CompareBuilder.build(strategies: s.currentStrategies ?? [], calendar: s.calendar.value, limit: 3, count: 10))
        let sainfoin = try #require(compare.all.first { $0.id == "bc3_sainfoin_grass" })
        #expect(sainfoin.rainFed && sainfoin.fit == .fits && sainfoin.waterText == "Rain-fed (no irrigation)")
        #expect(FieldNowBuilder.cropMapName(s.field) == "AAFC Annual Crop Inventory")
    }

    @Test("Year: typical year, the last 4 seasons, rain marks and the ML verdict")
    func year() async throws {
        let (a, s) = try await session("car_colusa_rice")
        let p = YearBuilder.build(field: s.field, calendar: try #require(s.calendar.value), ml: s.calendarML.value, models: s.models.value,
                                  daily: s.daily.value, stress: s.stress.value, waterSeen: s.waterSeen.value, today: a.today, earlier: false, detail: true)
        #expect(p.rows.map(\.year) == [2026, 2025, 2024, 2023])
        #expect(p.typical.count == 36)
        #expect(p.mlVerdict.available)
        #expect(p.rows.contains { $0.ticks.contains { if case .rain = $0.kind { true } else { false } } })
        let cal = try #require(s.calendar.value)
        let earlier = YearBuilder.build(field: s.field, calendar: cal, ml: nil, models: nil, daily: nil, stress: nil, waterSeen: nil,
                                        today: a.today, earlier: true, detail: false)
        #expect(earlier.rows.last?.year == 2016)
        #expect(!earlier.mlVerdict.available)
    }

    @Test("Compare: top 2, weather replays, and priorities re-scored through POST /score")
    func compare() async throws {
        let (_, s) = try await session("car_colusa_rice")
        let p = try #require(CompareBuilder.build(strategies: s.currentStrategies ?? [], calendar: s.calendar.value, limit: 5))
        #expect(p.today.name == "Rice + winter flood")
        #expect(p.top.map(\.id) == ["car2_dryyear_safflower", "car1_rice_wintercover"])
        #expect(p.top[0].gains.first?.title == "Needs less irrigation water")
        let dry = try #require(CompareBuilder.build(strategies: s.currentStrategies ?? [], calendar: s.calendar.value, limit: 5, weather: .dry))
        let base = try #require(s.currentStrategies?.first { $0.isBaseline })
        #expect(dry.today.water == CompareBuilder.waterNeed(base, .dry))

        s.rescoreDebounce = .milliseconds(5)
        #expect(s.scoreRequest(limit: 4).weights == nil)
        s.weights["water_use"] = 4
        s.scenario.dP_pct = -20
        let req = s.scoreRequest(limit: 4)
        #expect(req.weights?["water_use"] == 4 && req.weights?["pest_break"] == 0 && req.weights?["market"] == 0)
        #expect(req.scenario?.dP_pct == -20)
        s.scheduleRescore(limit: 4)
        await s.pendingRescore?.value
        #expect(s.rescoreError == nil)
        #expect(s.currentStrategies?.count == 4)
    }

    @Test("Print: one-page US Letter PDF with the chosen option")
    func printPDF() async throws {
        let (a, s) = try await session("car_colusa_rice")
        let content = SummaryBuilder.content(session: s, limit: .init(value: 5, isExample: true), today: a.today, pick: "car3_rice_wheat")
        #expect(content.alternative?.id == "car3_rice_wheat")
        #expect(content.now.count == 4 && content.season.count == 3)
        #expect(content.stateFieldNumber == "0605542")
        let url = try #require(PDFRenderer.pdf(SummaryPage(content: content, thumbnail: nil), name: content.fieldName))
        let pdf = try #require(CGPDFDocument(url as CFURL))
        #expect(pdf.numberOfPages == 1)
        #expect(pdf.page(at: 1)?.getBoxRect(.mediaBox).size == CGSize(width: 612, height: 792))
    }

    @Test("Water limit: example from the API until the grower sets one, saved per field")
    func limits() async throws {
        let limits = TestAPI.limits()
        _ = await app(limits: limits)
        #expect(limits.limit(for: "caf_tipton_forage") == .init(value: 3.0, isExample: true))
        limits.set(3.04, for: "car_colusa_rice")
        #expect(limits.limit(for: "car_colusa_rice") == .init(value: 3.0, isExample: false))
        limits.reset("car_colusa_rice")
        #expect(limits.limit(for: "car_colusa_rice").isExample)
    }
}
