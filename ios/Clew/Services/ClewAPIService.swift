import Foundation
import Combine

/// REST & SSE API Client for Clew FastAPI Proxy Server
public final class ClewAPIService: @unchecked Sendable {
    public static let shared = ClewAPIService()
    
    /// Base URL configured for Tailscale mesh IP or local testing
    public var baseURL: String = AppEnvironment.baseURL
    
    private init() {}
    
    /// Fetches active working state tasks from /api/tasks
    public func fetchWorkingState() async throws -> [TaskItem] {
        guard let url = URL(string: "\(baseURL)/api/tasks") else {
            throw URLError(.badURL)
        }
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode([TaskItem].self, from: data)
    }
    
    /// Sends prompt command to /api/chat
    public func sendPrompt(_ prompt: String, tetherID: String = "mobile_default") async throws -> String {
        guard let url = URL(string: "\(baseURL)/api/chat") else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: String] = [
            "prompt": prompt,
            "goal_tether_id": tetherID
        ]
        request.httpBody = try JSONEncoder().encode(body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
        
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let responseText = json["response"] as? String {
            return responseText
        }
        
        return "Command processed."
    }
    
    /// Connects to /api/chat/stream and yields token strings as they arrive from Broca's Area.
    public func streamPrompt(_ prompt: String, tetherID: String = "mobile_default") -> AsyncThrowingStream<String, Error> {
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
    public func createTask(title: String, priority: TaskPriority, energyLevel: EnergyLevel) async throws -> Int64 {
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
    public func updateTaskStatus(id: Int64, status: String) async throws -> Bool {
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
    
    /// Fetches LiveKit WebRTC session credentials from /api/livekit/token
    public func fetchLiveKitToken() async throws -> LiveKitSessionInfo {
        guard let url = URL(string: "\(baseURL)/api/livekit/token") else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse,
                  (200...299).contains(httpResponse.statusCode) else {
                throw URLError(.badServerResponse)
            }
            return try JSONDecoder().decode(LiveKitSessionInfo.self, from: data)
        } catch {
            // Fallback mock session token for offline testing
            return LiveKitSessionInfo(
                token: "mock_jwt_token",
                url: "wss://clew-livekit.local:7880",
                room: "clew-default-room"
            )
        }
    }
}
