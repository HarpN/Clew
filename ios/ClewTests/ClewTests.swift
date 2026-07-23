import XCTest
@testable import Clew

final class ClewTests: XCTestCase {

    func testTaskItemDecodingP1() throws {
        let json = """
        {
            "id": 42,
            "title": "Calibrate WebRTC Engine",
            "description": "Sub-500ms latency test",
            "category": "voice",
            "priority": "P1",
            "energy_level": "high",
            "status": "pending",
            "created_at": "2026-07-22 17:00:00"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let task = try decoder.decode(TaskItem.self, from: json)

        XCTAssertEqual(task.id, 42)
        XCTAssertEqual(task.title, "Calibrate WebRTC Engine")
        XCTAssertEqual(task.priority, .p1)
        XCTAssertEqual(task.energyLevel, .high)
    }

    func testLimbicStateUnitPointCalculation() {
        let limbic = LimbicState(valence: 0.5, arousal: 0.5, dominance: 0.0, activeMood: "Testing")
        let point = limbic.unitPoint

        XCTAssertEqual(point.x, 0.75, accuracy: 0.001)
        XCTAssertEqual(point.y, 0.25, accuracy: 0.001)
        XCTAssertEqual(limbic.quadrantName, "Focused High Energy")
    }

    func testChatMessageInitialization() {
        let msg = ChatMessage(speaker: .user, content: "Test prompt", source: "unit_test")
        XCTAssertEqual(msg.speaker, .user)
        XCTAssertEqual(msg.content, "Test prompt")
        XCTAssertEqual(msg.source, "unit_test")
    }

    func testAppEnvironmentDefaultConfig() {
        let env = AppEnvironment(baseURL: "https://test.local:8000")
        XCTAssertEqual(env.baseURL, "https://test.local:8000")
    }
}
