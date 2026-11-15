import XCTest

/// Runs the app on bundled fixtures (-ui-testing): pick a field, read Field now, change the water limit, make the summary.
final class CropLyticsUITests: XCTestCase {
    override func setUp() {
        continueAfterFailure = false
    }

    @MainActor
    func testPickFieldThenCompareAndSummary() {
        let app = XCUIApplication()
        app.launchArguments = ["-ui-testing"]
        app.launch()

        let field = app.buttons["field-car_colusa_rice"]
        XCTAssertTrue(field.waitForExistence(timeout: 10), "The field list shows the Colusa rice field")
        field.tap()

        XCTAssertTrue(app.staticTexts["How much rain so far this season?"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.otherElements["field-summary"].exists || app.staticTexts["Your field now"].exists)

        app.tabBars.buttons["Compare"].tap()
        let limit = app.staticTexts["limit-value"]
        XCTAssertTrue(limit.waitForExistence(timeout: 10))
        XCTAssertEqual(limit.label, "5.0 acre-ft/acre")
        let stepper = app.steppers["limit-stepper"]
        XCTAssertTrue(stepper.exists)
        stepper.buttons.element(boundBy: 0).tap() // decrement by 0.1
        XCTAssertEqual(limit.label, "4.9 acre-ft/acre")
        XCTAssertTrue(app.staticTexts["You gain"].firstMatch.waitForExistence(timeout: 10))

        app.tabBars.buttons["Summary"].tap()
        XCTAssertTrue(app.buttons["share-pdf"].waitForExistence(timeout: 20), "The PDF is ready to share")
    }

    @MainActor
    func testSearchFiltersFields() {
        let app = XCUIApplication()
        app.launchArguments = ["-ui-testing"]
        app.launch()
        XCTAssertTrue(app.buttons["field-caf_tulare_forage"].waitForExistence(timeout: 10))
        let search = app.searchFields.firstMatch
        if !search.exists { app.swipeDown() }
        search.tap()
        search.typeText("Kings")
        XCTAssertTrue(app.buttons["field-caf_tulare_forage"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["field-car_colusa_rice"].exists)
    }
}
