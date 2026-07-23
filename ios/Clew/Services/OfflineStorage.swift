import Foundation

/// Offline Cache & CRDT Local Storage Coordinator
/// Manages SQLite/GRDB local database tables and pending mutation queues.
final class OfflineStorage {
    static let shared = OfflineStorage()
    
    private let cacheFileName = "clew_working_state_cache.json"
    private var fileURL: URL {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        return docs.appendingPathComponent(cacheFileName)
    }
    
    private init() {}
    
    /// Save tasks locally for offline resilience
    func saveCachedTasks(_ tasks: [TaskItem]) {
        do {
            let data = try JSONEncoder().encode(tasks)
            try data.write(to: fileURL, options: .atomic)
        } catch {
            print("[OfflineStorage] Error saving local task cache: \(error)")
        }
    }
    
    /// Load cached tasks when offline
    func loadCachedTasks() -> [TaskItem] {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return [] }
        do {
            let data = try Data(contentsOf: fileURL)
            return try JSONDecoder().decode([TaskItem].self, from: data)
        } catch {
            print("[OfflineStorage] Error reading local task cache: \(error)")
            return []
        }
    }
}
