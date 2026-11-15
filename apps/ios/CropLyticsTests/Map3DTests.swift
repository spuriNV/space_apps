import XCTest
@testable import CropLytics

final class Map3DTests: XCTestCase {
    func testZoomFractionWindow() {
        XCTAssertEqual(Map3D.zoomFraction(5), 0)
        XCTAssertEqual(Map3D.zoomFraction(12.2), 0, accuracy: 1e-9)
        XCTAssertEqual(Map3D.zoomFraction(13.2), 1.0 / 1.7, accuracy: 1e-9)
        XCTAssertEqual(Map3D.zoomFraction(14.2), 1)
        XCTAssertEqual(Map3D.zoomFraction(18), 1)
        XCTAssertEqual(Map3D.pitch(forFraction: 1), 58)
        XCTAssertEqual(Map3D.bearing(forFraction: 0), 0)
        XCTAssertEqual(Map3D.bearing(forFraction: 0.5), -11, accuracy: 1e-9)
        XCTAssertFalse(Map3D.isDrilled(zoom: 14, fieldOpen: false))
        XCTAssertTrue(Map3D.isDrilled(zoom: 13.5, fieldOpen: true))
        XCTAssertFalse(Map3D.isDrilled(zoom: 13.4, fieldOpen: true))
    }

    func testCellHeightsAndColours() {
        let s = 1.0
        XCTAssertEqual(Map3D.cellHeight(ndvi: 1, scale: s).base, 430)
        XCTAssertEqual(Map3D.cellHeight(ndvi: 1, scale: s).top, 430 + 183)
        XCTAssertEqual(Map3D.cellHeight(ndvi: nil, scale: s).top, 430 + 8)
        XCTAssertEqual(Map3D.cellHeight(ndvi: 2, scale: 2).top, 2 * 430 + 2 * 183)
        XCTAssertEqual(Map3D.cellColor(0.1), "#A8703F")
        XCTAssertEqual(Map3D.cellColor(0.5), "#2F9E4B")
        XCTAssertEqual(Map3D.ndvi(["2024_q4": 0.4], year: 2025, month: 2), 0.4)
        XCTAssertNil(Map3D.ndvi([:], year: 2025, month: 2))
    }

    func testStackOrderAndExtrusions() {
        let ring: [(lon: Double, lat: Double)] = [(-122.0, 39.0), (-121.99, 39.0), (-121.99, 39.01), (-122.0, 39.01)]
        let st = Map3D.stack(rings: [ring], lat: 39.0, cells: [(ring, 0.6)], soilPct: 84, groundwaterPct: 20)!
        XCTAssertEqual(st.cells.count, 1)
        XCTAssertEqual(st.cells[0].ring.first, st.cells[0].ring.last)
        XCTAssertGreaterThan(st.smap[0].base, st.grace[0].base)
        XCTAssertGreaterThan(st.cells[0].base, st.smap[0].height)
        XCTAssertEqual(st.posts.count, 4)
        XCTAssertEqual(st.soilWords, "Wetter than usual (84th percentile)")
        XCTAssertEqual(st.groundwaterWords, "Less than usual (20th percentile)")
    }

    func testWordsAndFootprints() {
        XCTAssertEqual(Map3D.soilWords(nil), "No reading")
        XCTAssertEqual(Map3D.soilWords(50), "About normal (50th percentile)")
        XCTAssertEqual(Map3D.footprintMiles(degrees: 0.09), 6)
        XCTAssertEqual(Map3D.footprintMiles(degrees: 0.25), 17)
        XCTAssertEqual(Map3D.footprintLabel(word: "Soil moisture", degrees: 0.09), "Soil moisture: this 6-mile square")
        XCTAssertEqual(Map3D.smapColor(nil), "#737A86")
    }
}
