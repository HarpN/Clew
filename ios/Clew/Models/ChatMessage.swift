import Foundation

enum MessageSpeaker: String, Codable, Sendable {
    case user = "user"
    case agent = "agent"
    case system = "system"
}

struct ChatMessage: Identifiable, Decodable, Equatable, Sendable {
    let id: String
    let speaker: MessageSpeaker
    let content: String
    let timestamp: Date
    let source: String
    
    enum CodingKeys: String, CodingKey {
        case id
        case speaker
        case content
        case timestamp
        case source
    }
    
    init(
        id: String = UUID().uuidString,
        speaker: MessageSpeaker,
        content: String,
        timestamp: Date = Date(),
        source: String = "mobile_native"
    ) {
        self.id = id
        self.speaker = speaker
        self.content = content
        self.timestamp = timestamp
        self.source = source
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        
        if let idInt = try? container.decode(Int.self, forKey: .id) {
            self.id = String(idInt)
        } else if let idStr = try? container.decode(String.self, forKey: .id) {
            self.id = idStr
        } else {
            self.id = UUID().uuidString
        }
        
        if let spStr = try? container.decode(String.self, forKey: .speaker),
           let sp = MessageSpeaker(rawValue: spStr.lowercased()) {
            self.speaker = sp
        } else {
            self.speaker = .agent
        }
        
        self.content = try container.decodeIfPresent(String.self, forKey: .content) ?? ""
        self.source = try container.decodeIfPresent(String.self, forKey: .source) ?? "mobile_native"
        
        if let dateVal = try? container.decode(Date.self, forKey: .timestamp) {
            self.timestamp = dateVal
        } else {
            self.timestamp = Date()
        }
    }
}
