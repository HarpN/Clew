import Foundation

enum TaskPriority: String, Codable, CaseIterable {
    case p1 = "P1"
    case p2 = "P2"
    case p3 = "P3"
    
    var colorName: String {
        switch self {
        case .p1: return "red"
        case .p2: return "orange"
        case .p3: return "blue"
        }
    }
}

enum EnergyLevel: String, Codable, CaseIterable {
    case high = "high"
    case medium = "medium"
    case low = "low"
    
    var iconName: String {
        switch self {
        case .high: return "bolt.fill"
        case .medium: return "bolt.horizontal.fill"
        case .low: return "battery.25"
        }
    }
}

struct TaskItem: Identifiable, Codable {
    let id: Int64
    var title: String
    var description: String?
    var category: String
    var priority: TaskPriority
    var energyLevel: EnergyLevel
    var status: String
    var time: String
    
    enum CodingKeys: String, CodingKey {
        case id
        case title
        case description
        case category
        case priority
        case energyLevel = "energy_level"
        case status
        case time
        case createdAt = "created_at"
    }
    
    init(
        id: Int64,
        title: String,
        description: String? = nil,
        category: String = "general",
        priority: TaskPriority = .p2,
        energyLevel: EnergyLevel = .medium,
        status: String = "pending",
        time: String = "Today"
    ) {
        self.id = id
        self.title = title
        self.description = description
        self.category = category
        self.priority = priority
        self.energyLevel = energyLevel
        self.status = status
        self.time = time
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try container.decode(Int64.self, forKey: .id)
        self.title = try container.decode(String.self, forKey: .title)
        self.description = try container.decodeIfPresent(String.self, forKey: .description)
        self.category = try container.decodeIfPresent(String.self, forKey: .category) ?? "general"
        
        // Priority parsing (support P1, P2, P3 or Int 1, 2, 3)
        if let pString = try? container.decode(String.self, forKey: .priority),
           let pVal = TaskPriority(rawValue: pString.uppercased()) {
            self.priority = pVal
        } else if let pInt = try? container.decode(Int.self, forKey: .priority) {
            switch pInt {
            case 1: self.priority = .p1
            case 3: self.priority = .p3
            default: self.priority = .p2
            }
        } else {
            self.priority = .p2
        }
        
        // Energy Level parsing
        if let eString = try? container.decode(String.self, forKey: .energyLevel),
           let eVal = EnergyLevel(rawValue: eString.lowercased()) {
            self.energyLevel = eVal
        } else {
            self.energyLevel = .medium
        }
        
        self.status = try container.decodeIfPresent(String.self, forKey: .status) ?? "pending"
        
        if let tString = try container.decodeIfPresent(String.self, forKey: .time) {
            self.time = tString
        } else if let cString = try container.decodeIfPresent(String.self, forKey: .createdAt) {
            self.time = cString
        } else {
            self.time = "Today"
        }
    }
}
