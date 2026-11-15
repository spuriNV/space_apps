import XCTest

/// Runs the app on bundled fixtures (-ui-testing): pick a field on the sheet over the map, read Field now,
/// change the water limit on Compare, make the PDF; filter the pick list; move the viewing date.
final class CropLyticsUITests: XCTestCase {
    override func setUp() {
        continueAfterFailure = false
    }

    @MainActor
    private func launch(_ extra: [String] = []) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["-ui-testing"] + extra
        app.launch()
        return app
    }

    @MainActor
    func testPickFieldThenCompareAndPrint() {
        let app = launch()
        let field = app.buttons["field-car_colusa_rice"]
        XCTAssertTrue(field.waitForExistence(timeout: 15), "The pick list shows the Colusa rice field")
        field.tap()

        XCTAssertTrue(app.staticTexts["How much rain so far this season?"].waitForExistence(timeout: 15))
        XCTAssertTrue(app.buttons["tab-now"].isSelected)

        app.buttons["tab-compare"].tap()
        let limit = app.staticTexts["limit-value"]
        XCTAssertTrue(limit.waitForExistence(timeout: 10))
        XCTAssertEqual(limit.label, "5.0 acre-ft/acre")
        app.steppers["limit-stepper"].buttons.element(boundBy: 0).tap()
        XCTAssertEqual(limit.label, "4.9 acre-ft/acre")

        app.buttons["tab-print"].tap()
        XCTAssertTrue(app.buttons["share-pdf"].waitForExistence(timeout: 20), "The PDF is ready to share")
    }

    @MainActor
    func testChipsAndSearchFilterThePickList() {
        let app = launch()
        XCTAssertTrue(app.buttons["field-bc_salmon_river_forage"].waitForExistence(timeout: 15))
        app.buttons["chip-bc"].tap()
        XCTAssertTrue(app.buttons["field-bc_salmon_river_forage"].exists)
        XCTAssertFalse(app.buttons["field-car_colusa_rice"].exists)
        app.buttons["chip-bc"].tap()
        let search = app.textFields.firstMatch
        search.tap()
        search.typeText("Williams")
        XCTAssertTrue(app.buttons["field-car_colusa_rice"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["field-caf_tulare_forage"].exists)
    }

    @MainActor
    func testViewingDateAndBackToToday() {
        let app = launch(["-initialField", "car_colusa_rice"])
        let date = app.buttons["date-control"]
        XCTAssertTrue(date.waitForExistence(timeout: 15))
        date.tap()
        let floods = app.buttons["quick-2023 floods"]
        XCTAssertTrue(floods.waitForExistence(timeout: 5))
        floods.tap()
        XCTAssertTrue(app.staticTexts["Your field in mid Mar 2023"].waitForExistence(timeout: 10))
        app.buttons["back-to-today"].tap()
        XCTAssertTrue(app.staticTexts["Your field now"].waitForExistence(timeout: 10))
    }
}
