import XCTest

/// A pinch into the open field raises the stack, tilts once the fingers lift, and a second pinch still zooms.
final class MapPinchUITests: XCTestCase {
    @MainActor
    private func state(_ app: XCUIApplication) -> (zoom: Double, pitch: Double) {
        let parts = app.otherElements["map-state"].label.split(separator: " ")
        return (Double(parts[1]) ?? 0, Double(parts[3]) ?? 0)
    }

    @MainActor
    func testPinchTiltsAndSecondPinchStillZooms() {
        let app = XCUIApplication()
        app.launchArguments = ["-ui-testing", "-initialField", "car_colusa_rice", "-sheet", "peek"]
        app.launch()
        let label = app.otherElements["map-state"]
        XCTAssertTrue(label.waitForExistence(timeout: 20))
        sleep(6) // card flight and tiles
        let z0 = state(app).zoom
        app.windows.firstMatch.pinch(withScale: 4, velocity: 1.5)
        sleep(2)
        let a = state(app)
        XCTAssertGreaterThan(a.zoom, z0 + 0.8, "first pinch zooms in")
        app.windows.firstMatch.pinch(withScale: 2, velocity: 1.5)
        sleep(2)
        let b = state(app)
        XCTAssertGreaterThan(b.zoom, a.zoom + 0.4, "second pinch still zooms")
        XCTAssertGreaterThan(b.pitch, 10, "pitch follows zoom once the pinch ends")
        print("MAPSTATE z0=\(z0) after1=\(a) after2=\(b)")
    }
}
