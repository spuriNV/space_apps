import XCTest

/// Phone shot: Safari already shows https://croplytics-app.onrender.com (opened by record-phone.sh).
/// Taps the Colusa rice card, lets the map fly in and the data load, then pulls the field sheet up.
/// Prints MARK lines with timestamps so the recording can be cut to the tap.
final class SafariShotTests: XCTestCase {
    @MainActor
    func testColusaFlyIn() throws {
        let safari = XCUIApplication(bundleIdentifier: "com.apple.mobilesafari")
        safari.activate()
        let card = safari.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS[c] %@", "4 miles east of Williams")).firstMatch
        let found = card.waitForExistence(timeout: 60)
        print("MARK found=\(found)")
        sleep(UInt32(ProcessInfo.processInfo.environment["PRE_WAIT"] ?? "3") ?? 3)
        print("MARK tap \(Date().timeIntervalSince1970)")
        if found && card.isHittable { card.tap() } else {
            // the card's position in the phone layout (pick list open over California)
            safari.coordinate(withNormalizedOffset: CGVector(dx: 0.55, dy: 0.40)).tap()
        }
        sleep(2)
        print("MARK flown \(Date().timeIntervalSince1970)")
        // wait for the field's numbers (water need) before moving the sheet; the edit cuts the wait out
        let need = safari.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS %@", "acre-ft/acre")).firstMatch
        print("MARK loaded=\(need.waitForExistence(timeout: 60)) \(Date().timeIntervalSince1970)")
        let na = safari.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS %@", "Not available")).firstMatch
        print("MARK live=\(!na.exists)")
        sleep(2)
        // the sheet's handle cycles half -> full, so "Your field now" shows rain and water need
        let grab = safari.buttons["Resize the field panel"].firstMatch
        print("MARK grab=\(grab.exists) \(Date().timeIntervalSince1970)")
        // fling the sheet up from its handle (the redesign snaps peek / half / full by velocity)
        let from = safari.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.378))
        from.press(forDuration: 0.05, thenDragTo: safari.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.10)), withVelocity: .fast, thenHoldForDuration: 0)
        sleep(1)
        let rain = safari.descendants(matching: .any).matching(NSPredicate(format: "label BEGINSWITH %@", "Rain since")).firstMatch
        print("MARK rain-visible=\(rain.exists && rain.isHittable)")
        if !(rain.exists && rain.isHittable) && grab.exists { grab.tap(); print("MARK grab-tap \(Date().timeIntervalSince1970)") }
        sleep(4)
        print("MARK end \(Date().timeIntervalSince1970)")
    }
}
