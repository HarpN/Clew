import Foundation
import Combine

final class ClewAPIService {
    static let shared = ClewAPIService()
    
    // Configured to point to Tailscale IP or Local Server
    @Published var baseURL: String = AppEnvironment.shared.baseURL
    
    private var cancellables = Set<AnyCancellable>()
    
    init() {
        AppEnvironment.shared.$baseURL
            .sink { [weak self] newURL in
                self?.baseURL = newURL
            }
            .store(in: &cancellables)
    }
    
    /// Fetch all tasks from working state database
    func fetchWorkingState() async throws -> [TaskItem] {
        guard let url = URL(string: "\(baseURL)/api/tasks") else {
            throw URLError(.badURL)
        }
        let (data, response) = try await URLSession.shared.data(from: url)
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode([TaskItem].self, from: data)
    }
    
    /// Submit prompt/dialogue to Clew brain orchestrator (unary response)
    func sendPrompt(_ prompt: String) async throws -> String {
        guard let url = URL(string: "\(baseURL)/api/chat") else {
            throw URLError(.badURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "message": prompt,
            "source": "ios_native_client"
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
        
        let responseDict = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        return responseDict?["reply"] as? String ?? responseDict?["response"] as? String ?? "No response"
    }
    
    /// Connects to /api/chat/stream and yields token strings as they arrive from Broca's Area.
    func streamPrompt(_ prompt: String, tetherID: String = "mobile_default") -> AsyncThrowingStream<String, Error> {
        AsyncThrowingStream { continuation in
            Task {
                guard let url = URL(string: "\(self.baseURL)/api/chat/stream") else {
                    continuation.finish(throwing: URLError(.badURL))
                    return
                }
                
                var request = URLRequest(url: url)
                request.httpMethod = "POST"
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
                
                let body: [String: Any] = [
                    "prompt": prompt,
                    "goal_tether_id": tetherID
                ]
                request.httpBody = try? JSONSerialization.data(withJSONObject: body)
                
                do {
                    let (bytes, response) = try await URLSession.shared.bytes(for: request)
                    
                    guard let httpResponse = response as? HTTPURLResponse,
                          (200...299).contains(httpResponse.statusCode) else {
                        continuation.finish(throwing: URLError(.badServerResponse))
                        return
                    }
                    
                    for try await line in bytes.lines {
                        if line.hasPrefix("data: ") {
                            let dataString = String(line.dropFirst(6)).trimmingCharacters(in: .whitespaces)
                            
                            if dataString == "[DONE]" {
                                continuation.finish()
                                break
                            }
                            
                            if let data = dataString.data(using: .utf8),
                               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                               let type = json["type"] as? String {
                                
                                if type == "token", let token = json["text"] as? String {
                                    continuation.yield(token)
                                } else if type == "veto", let vetoText = json["text"] as? String {
                                    continuation.yield(vetoText)
                                }
                            }
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }
    
    /// Create a new task item
    func createTask(title: String, priority: TaskPriority, energyLevel: EnergyLevel) async throws -> Int64 {
        guard let url = URL(string: "\(baseURL)/api/tasks") else {
            throw URLError(.badURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "title": title,
            "priority": priority.rawValue,
            "energy_level": energyLevel.rawValue
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, _) = try await URLSession.shared.data(for: request)
        let dict = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        return (dict?["task_id"] as? Int64) ?? 0
    }
    
    /// Update task status
    func updateTaskStatus(id: Int64, status: String) async throws -> Bool {
        guard let url = URL(string: "\(baseURL)/api/tasks/\(id)/status") else {
            throw URLError(.badURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = ["status": status]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, _) = try await URLSession.shared.data(for: request)
        let dict = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        return (dict?["success"] as? Bool) ?? false
    }
    
    /// Fetch token for LiveKit sub-500ms WebRTC voice session
    func fetchLiveKitToken() async throws -> (token: String, url: String, room: String) {
        guard let url = URL(string: "\(baseURL)/api/livekit/token") else {
            throw URLError(.badURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let (data, _) = try await URLSession.shared.data(for: request)
        let dict = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        
        let token = dict?["token"] as? String ?? ""
        let livekitURL = dict?["url"] as? String ?? AppEnvironment.shared.liveKitURL
        let room = dict?["room"] as? String ?? "clew-voice-room"
        
        return (token: token, url: livekitURL, room: room)
    }
}
