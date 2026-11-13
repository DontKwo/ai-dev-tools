import XCTest

public class IosAuditDriver {
    let app: XCUIApplication
    var interactions: [[String: Any]] = []
    var seq = 0

    public init(app: XCUIApplication) {
        self.app = app
    }

    public func realClick(id: String) {
        let element = app.buttons[id]
        XCTAssertTrue(element.isHittable)
        element.tap()
        seq += 1
        interactions.append([
            "control_id": id,
            "input_kind": "touch",
            "trusted": true,
            "control_state": "enabled",
            "sequence_number": seq
        ])
    }
}
