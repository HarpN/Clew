import Foundation
import Combine

@MainActor
public final class DailyBriefViewModel: ObservableObject {
    @Published public var tasks: [TaskItem] = []
    @Published public var chatMessages: [String] = []
    @Published public var isTasksTowerExpanded: Bool = true
    @Published public var isProjectsTowerExpanded: Bool = false
    @Published public var isCalendarTowerExpanded: Bool = false
    @Published public var isLoading: Bool = false
    @Published public var errorMessage: String? = nil
    
    public init() {}
    
    public func loadState() async {
        self.isLoading = true
        self.errorMessage = nil
        do {
            let fetchedTasks = try await ClewAPIService.shared.fetchWorkingState()
            self.tasks = fetchedTasks
            OfflineStorage.shared.saveCachedTasks(fetchedTasks)
        } catch {
            print("[DailyBriefViewModel] Failed to fetch remote working state: \(error). Loading offline cache.")
            self.tasks = OfflineStorage.shared.loadCachedTasks()
            if self.tasks.isEmpty {
                self.errorMessage = "Unable to connect to Clew engine."
            }
        }
        self.isLoading = false
    }
    
    public func resolveTask(id: Int64) {
        self.tasks.removeAll { $0.id == id }
        OfflineStorage.shared.saveCachedTasks(self.tasks)
    }
    
    public func addTask(title: String, category: String = "home", priority: TaskPriority = .p2, energy: EnergyLevel = .medium) {
        let newTask = TaskItem(
            id: Int64(Date().timeIntervalSince1970 * 1000),
            title: title,
            category: category,
            priority: priority,
            energyLevel: energy,
            status: "pending",
            time: Date().formatted(date: .omitted, time: .shortened)
        )
        self.tasks.insert(newTask, at: 0)
        OfflineStorage.shared.saveCachedTasks(self.tasks)
    }
}
