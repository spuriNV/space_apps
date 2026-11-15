import Foundation
import Testing
@testable import CropLytics

@Suite("Grower units and words")
struct DomainTests {
    @Test("Pixel sizes become grower distances", arguments: [
        ("about 50 km (0.5 x 0.625 deg)", "about 31 miles"),
        ("30 m, every 2-3 days", "100 ft, every 2-3 days"),
        ("9 km, daily", "6 miles, daily"),
        ("70 m, irregular (ISS overpasses)", "230 ft, irregular (ISS overpasses)"),
    ])
    func distances(raw: String, expected: String) {
        #expect(Units.distanceInGrowerUnits(raw) == expected)
    }

    @Test func ordinals() {
        #expect([1, 2, 3, 4, 11, 12, 13, 21, 52, 53].map(Units.ordinal) == ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "52nd", "53rd"])
    }

    @Test func cropNames() {
        #expect(FieldNaming.cropName("Fallow/Idle Cropland") == "Left fallow")
        #expect(FieldNaming.cropName("Dbl Crop WinWht/Corn") == "Wheat, then corn")
        #expect(FieldNaming.cropName(nil) == "Not recorded")
        #expect(FieldNaming.mainCrop(["2023": "Corn", "2024": "Alfalfa", "2025": "Alfalfa"]) == "Alfalfa")
    }

    @Test func nearTown() {
        #expect(FieldNaming.nearTown(lat: 39.141386, lon: -122.083339, county: "Colusa") == "3.5 miles east of Williams")
        #expect(FieldNaming.nearTown(lat: 34.0, lon: -118.0, county: "Los Angeles") == "in Los Angeles County")
    }

    @Test("Gain or give-up only when the likely ranges don't overlap")
    func verdicts() {
        #expect(CompareBuilder.verdict(NumRange(2, low: 1.5, high: 2.5), NumRange(5, low: 4.5, high: 6)) == .better)
        #expect(CompareBuilder.verdict(NumRange(5, low: 4.5, high: 6), NumRange(2, low: 1.5, high: 2.5)) == .worse)
        #expect(CompareBuilder.verdict(NumRange(4, low: 3, high: 5), NumRange(4.5, low: 4, high: 6)) == .unclear)
        #expect(CompareBuilder.verdict(nil, NumRange(1)) == .none)
        #expect(CompareBuilder.fit(NumRange(4, low: 3, high: 5), limit: 4.5) == .mayExceed)
    }

    @Test("Calendar segments become 36 ten-day steps")
    func calendarClasses() throws {
        let cal = FieldCalendar(source: "hls", lastObservation: "2025-12-31", years: [
            .init(year: 2025, segments: [
                .init(startDoy: 1, endDoy: 59, cls: "water"),
                .init(startDoy: 60, endDoy: 150, cls: "bare"),
                .init(startDoy: 151, endDoy: 365, cls: "covered"),
            ]),
        ])
        let c = cal.classes(for: 2025)
        #expect(c.count == 36)
        #expect(c[0] == .water)
        #expect(c[6] == .bare)
        #expect(c[30] == .covered)
        #expect(cal.bareDays(in: 2025) == 91)
        #expect(cal.classes(for: 2026).allSatisfy { $0 == .noView })
    }

    @Test("SourcedNumber decodes objects and bare numbers")
    func sourcedNumber() throws {
        let a = try JSONDecoder().decode(SourcedNumber.self, from: Data(#"{"value": 5.2, "low": null, "high": "6.4"}"#.utf8))
        #expect(a == SourcedNumber(value: 5.2, low: nil, high: 6.4))
        let b = try JSONDecoder().decode(SourcedNumber.self, from: Data("49".utf8))
        #expect(b.value == 49)
    }

    @Test("Summary review notes drop internal references")
    @MainActor func plainReviewNotes() {
        #expect(SummaryViewModel.plain("Every alternative needs review before anything is seeded (spec B11).") == "Every alternative needs review before anything is seeded.")
        #expect(SummaryViewModel.plain("flood depth is not modelled (U); habitat value not scored") == "flood depth is not modelled; habitat value not scored")
    }
}
