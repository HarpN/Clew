import Foundation
import GRDB

/// Offline Cache & CRDT Local Storage Coordinator
/// Manages SQLite/GRDB local database tables and pending mutation queues.
public final class OfflineStorage: @unchecked Sendable {
    public static let shared = OfflineStorage()
    
    private var dbQueue: DatabaseQueue?
    private let cacheFileName = "clew_working_state_cache.json"
    
    private var fileURL: URL {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        return docs.appendingPathComponent(cacheFileName)
    }
    
    private init() {
        setupDatabase()
    }
    
    private func setupDatabase() {
        do {
            let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            let dbURL = docs.appendingPathComponent("clew_offline.sqlite")
            
            var config = Configuration()
            config.qos = .userInitiated
            
            let queue = try DatabaseQueue(path: dbURL.path, configuration: config)
            
            var migrator = DatabaseMigrator()
            migrator.registerMigration("v1_create_tasks") { db in
                try db.create(table: "taskRecord", ifNotExists: true) { t in
                    t.column("id", .integer).primaryKey()
                    t.column("title", .text).notNull()
                    t.column("category", .text).notNull()
                    t.column("priority", .text).notNull()
                    t.column("energyLevel", .text).notNull()
                    t.column("status", .text).notNull()
                    t.column("time", .text).notNull()
                }
            }
            
            try migrator.migrate(queue)
            self.dbQueue = queue
        } catch {
            print("[OfflineStorage] GRDB Database initialization warning: \(error). Falling back to JSON cache.")
        }
    }
    
    /// Save tasks locally for offline resilience using atomic file writes & GRDB transaction
    public func saveCachedTasks(_ tasks: [TaskItem]) {
        // 1. Write to JSON cache file
        do {
            let data = try JSONEncoder().encode(tasks)
            try data.write(to: fileURL, options: .atomic)
        } catch {
            print("[OfflineStorage] Error saving local task JSON cache: \(error)")
        }
        
        // 2. Sync to GRDB database queue
        guard let dbQueue = dbQueue else { return }
        do {
            try dbQueue.write { db in
                try db.execute(sql: "DELETE FROM taskRecord")
                for task in tasks {
                    try db.execute(
                        sql: """
                        INSERT INTO taskRecord (id, title, category, priority, energyLevel, status, time)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        arguments: [task.id, task.title, task.category, task.priority.rawValue, task.energyLevel.rawValue, task.status, task.time]
                    )
                }
            }
        } catch {
            print("[OfflineStorage] GRDB transaction error: \(error)")
        }
    }
    
    /// Load cached tasks when offline
    public func loadCachedTasks() -> [TaskItem] {
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
