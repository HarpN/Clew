import Foundation

public enum AppEnvironment {
    /// Active API Proxy Base URL pointing to local server or Tailscale mesh IP
    public static var baseURL: String {
        #if DEBUG
        return ProcessInfo.processInfo.environment["CLEW_API_URL"] ?? "http://127.0.0.1:8000"
        #else
        return "http://100.110.120.130:8000" // Tailscale mesh IP
        #endif
    }
    
    public static let appVersion = "5.0.0"
    public static let buildNumber = "1"
}
