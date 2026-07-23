import Foundation
import GRDB

public enum TaskPriority: String, Codable, CaseIterable, Sendable {
    case p1 = "P1"
    case p2 = "P2"
    case p3 = "P3"
}

public enum EnergyLevel: String, Codable, CaseIterable, Sendable {
    case high = "high"
    case medium = "medium"
    case low = "low"
    
    public var iconName: String {
        switch self {
        case .high: return "bolt.fill"
        case .medium: return "bolt.horizontal.fill"
        case .low: return "battery.25"
        }
    }
}

/// Core Working State Task Item model conforming to GRDB TableRecord and Codable
public struct TaskItem: Identifiable, Codable, Sendable, FetchableRecord, PersistableRecord, TableRecord {
    public static let databaseTableName = "taskRecord"

    public var id: Int64
    public var title: String
    public var category: String
    public var priority: TaskPriority
    public var energyLevel: EnergyLevel
    public var status: String
    public var time: String

    public init(id: Int64, title: String, category: String, priority: TaskPriority, energyLevel: EnergyLevel, status: String, time: String) {
        self.id = id
        self.title = title
        self.category = category
        self.priority = priority
        self.energyLevel = energyLevel
        self.status = status
        self.time = time
    }
}
