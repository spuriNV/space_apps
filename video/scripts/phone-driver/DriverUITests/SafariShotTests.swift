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
        sleep(2)
        // the sheet's handle cycles half -> full, so "Your field now" shows rain and water need
        let grab = safari.buttons["Resize the field panel"].firstMatch
        print("MARK grab=\(grab.exists) \(Date().timeIntervalSince1970)")
        if grab.exists { grab.tap() }
        sleep(4)
        print("MARK end \(Date().timeIntervalSince1970)")
    }
}
