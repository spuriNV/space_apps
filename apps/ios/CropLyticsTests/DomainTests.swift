import Foundation
import Testing
@testable import CropLytics

@Suite("Grower units, words and timeline")
struct DomainTests {
    @Test("Pixel sizes become grower distances", arguments: [
        ("about 50 km (0.5 x 0.625 deg)", "about 31 miles"),
        ("30 m, every 2-3 days", "100 ft, every 2-3 days"),
        ("9 km, daily", "6 miles, daily"),
    ])
    func distances(raw: String, expected: String) {
        #expect(Units.distanceInGrowerUnits(raw) == expected)
    }

    @Test func ordinals() {
        #expect([1, 2, 3, 11, 12, 13, 21, 52, 53].map(Units.ordinal) == ["1st", "2nd", "3rd", "11th", "12th", "13th", "21st", "52nd", "53rd"])
    }

    @Test func cropNames() {
        #expect(FieldNaming.cropName("Fallow/Idle Cropland") == "Left fallow")
        #expect(FieldNaming.cropName("Dbl Crop WinWht/Corn") == "Wheat, then corn")
        #expect(FieldNaming.cropName("Not mapped (no data)") == "Not recorded")
        #expect(FieldNaming.cropName("Pasture / Forages") == "Hay and pasture")
        #expect(FieldNaming.mainCrop(["2023": "Corn", "2024": "Alfalfa", "2025": "Alfalfa"]) == "Alfalfa")
    }

    @Test func nearTown() {
        #expect(FieldNaming.nearTown(lat: 39.141386, lon: -122.083339, county: "Colusa") == "3.5 miles east of Williams")
        #expect(FieldNaming.nearTown(lat: 34.0, lon: -118.0, county: "Los Angeles") == "in Los Angeles County")
    }

    @Test("Ten-day steps: labels, quick picks and the month picker")
    func timeline() {
        let today = TimePoint(iso: "2026-11-14")!
        #expect(today.year == 2026 && today.dekad == 31 && today.label == "mid Nov 2026")
        #expect(TimePoint(year: 2023, dekad: 7).label == "mid Mar 2023")
        #expect(today.advanced(by: 5).year == 2027)
        let picks = QuickDates.picks(today: today)
        #expect(picks.map(\.label) == ["Today", "Last summer", "Last spring", "2023 floods", "2022 drought"])
        #expect(picks[1].t == TimePoint(year: 2026, dekad: 19))
        #expect(QuickDates.years(today: today, earlier: false) == [2026, 2025, 2024, 2023])
        #expect(QuickDates.years(today: today, earlier: true).last == 2016)
    }

    @Test("Gain or give-up only when the likely ranges don't overlap")
    func verdicts() {
        #expect(CompareBuilder.verdict(NumRange(2, low: 1.5, high: 2.5), NumRange(5, low: 4.5, high: 6)) == .better)
        #expect(CompareBuilder.verdict(NumRange(5, low: 4.5, high: 6), NumRange(2, low: 1.5, high: 2.5)) == .worse)
        #expect(CompareBuilder.verdict(NumRange(4, low: 3, high: 5), NumRange(4.5, low: 4, high: 6)) == .unclear)
        #expect(CompareBuilder.fit(NumRange(4, low: 3, high: 5), limit: 4.5) == .mayExceed)
    }

    @Test("Calendar segments become 36 ten-day steps; the typical year is the most common class")
    func calendarClasses() {
        let cal = FieldCalendar(source: "hls", lastObservation: "2025-12-31", years: [
            .init(year: 2025, segments: [.init(startDoy: 1, endDoy: 59, cls: "water"), .init(startDoy: 60, endDoy: 150, cls: "bare"), .init(startDoy: 151, endDoy: 365, cls: "covered")]),
        ])
        let c = cal.classes(for: 2025)
        #expect(c.count == 36 && c[0] == .water && c[6] == .bare && c[30] == .covered)
        #expect(cal.bareDays(in: 2025) == 91)
        #expect(YearBuilder.typical([c, c, Array(repeating: .bare, count: 36)])[30] == .covered)
    }

    @Test("Rain so far and heat from the daily record, against the same dates before")
    func dailyAnalysis() {
        var rows: [DailyRecord.Row] = []
        for y in 2019...2026 {
            rows.append(.init(date: "\(y)-10-15", imergMm: y == 2026 ? 10 : 20, tmaxC: 30, tminC: -1))
            rows.append(.init(date: "\(y)-11-02", imergMm: y == 2026 ? 10 : 20, tmaxC: 20, tminC: 5))
            if y < 2026 { rows.append(.init(date: "\(y + 1)-07-10", imergMm: 0, tmaxC: 41, tminC: 20)) }
        }
        let daily = DailyRecord(rows: rows.sorted { $0.date < $1.date })
        let t = TimePoint(iso: "2026-11-14")!
        let r = DailyAnalysis.rainSoFar(daily, at: t)
        #expect(r?.period.current == true)
        #expect(abs((r?.inches ?? 0) - 20 / 25.4) < 0.001)
        #expect(abs((r?.pct ?? 0) - 50) < 0.5)
        let h = DailyAnalysis.heatFrost(daily, at: TimePoint(iso: "2026-07-25")!)
        #expect(h?.hot == 1)
    }

    @Test("SourcedNumber decodes objects and bare numbers")
    func sourcedNumber() throws {
        let a = try JSONDecoder().decode(SourcedNumber.self, from: Data(#"{"value": 5.2, "low": null, "high": "6.4"}"#.utf8))
        #expect(a == SourcedNumber(value: 5.2, low: nil, high: 6.4))
        #expect(try JSONDecoder().decode(SourcedNumber.self, from: Data("49".utf8)).value == 49)
    }

    @Test("Summary review notes drop internal references")
    func plainReviewNotes() {
        #expect(SummaryBuilder.plain("Every alternative needs review before anything is seeded (spec B11).") == "Every alternative needs review before anything is seeded.")
        #expect(SummaryBuilder.plain("flood depth is not modelled (U); habitat value not scored") == "flood depth is not modelled; habitat value not scored")
    }
}
