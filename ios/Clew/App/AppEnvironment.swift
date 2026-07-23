import Foundation
import Combine

/// Environment configuration for Clew iOS & iPadOS native client.
/// Manages Tailscale IP, local gateway URLs, and engine connectivity settings.
final class AppEnvironment: ObservableObject {
    static let shared = AppEnvironment()
    
    @Published var baseURL: String
    @Published var liveKitURL: String
    @Published var isOfflineMode: Bool = false
    @Published var apiTimeout: TimeInterval = 10.0
    
    init(
        baseURL: String = "https://clew-brain.local:8000",
        liveKitURL: String = "wss://livekit.local"
    ) {
        self.baseURL = ProcessInfo.processInfo.environment["CLEW_BASE_URL"] ?? baseURL
        self.liveKitURL = ProcessInfo.processInfo.environment["LIVEKIT_URL"] ?? liveKitURL
    }
    
    func updateBaseURL(_ newURL: String) {
        var formatted = newURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if formatted.hasSuffix("/") {
            formatted.removeLast()
        }
        self.baseURL = formatted
    }
}
