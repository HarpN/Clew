import Foundation
import Combine

@MainActor
final class DailyBriefViewModel: ObservableObject {
    @Published var tasks: [TaskItem] = []
    @Published var chatMessages: [ChatMessage] = []
    @Published var limbicState: LimbicState = LimbicState()
    
    // Collapsible Tower Container Accordion States
    @Published var isTasksTowerExpanded: Bool = true
    @Published var isProjectsTowerExpanded: Bool = false
    @Published var isCalendarTowerExpanded: Bool = false
    
    @Published var isLoading: Bool = false
    @Published var statusMessage: String = "Ready"
    @Published var draftPrompt: String = ""
    
    init() {
        // Initial sample seed state while network connects
        self.chatMessages = [
            ChatMessage(speaker: .agent, content: "Clew V5 Native Engine initialized. Executive brief ready.", source: "system")
        ]
    }
    
    func loadState() async {
        self.isLoading = true
        self.statusMessage = "Syncing with Clew Brain..."
        
        do {
            let fetchedTasks = try await ClewAPIService.shared.fetchWorkingState()
            self.tasks = fetchedTasks
            OfflineStorage.shared.saveCachedTasks(fetchedTasks)
            self.statusMessage = "Tasks updated (\(fetchedTasks.count) active)"
        } catch {
            print("[iOS_CLIENT] Error loading tasks: \(error)")
            // Fallback to local offline storage cache
            let cached = OfflineStorage.shared.loadCachedTasks()
            if !cached.isEmpty {
                self.tasks = cached
                self.statusMessage = "Offline cache loaded (\(cached.count) tasks)"
            } else {
                self.statusMessage = "Offline - No cached tasks"
                // Seed fallback starter items
                self.tasks = [
                    TaskItem(id: 101, title: "Review WebRTC Audio Latency", category: "voice", priority: .p1, energyLevel: .high, status: "pending", time: "09:00 AM"),
                    TaskItem(id: 102, title: "Calibrate Limbic Compass Quadrants", category: "limbic", priority: .p2, energyLevel: .medium, status: "pending", time: "11:30 AM"),
                    TaskItem(id: 103, title: "Execute Nightly Distillation Cron", category: "cron", priority: .p3, energyLevel: .low, status: "pending", time: "05:00 PM")
                ]
            }
        }
        
        self.isLoading = false
    }
    
    func resolveTask(id: Int64) {
        self.tasks.removeAll { $0.id == id }
        Task {
            _ = try? await ClewAPIService.shared.updateTaskStatus(id: id, status: "completed")
        }
    }
    
    func addTask(title: String, priority: TaskPriority, energyLevel: EnergyLevel) {
        let tempId = Int64(Date().timeIntervalSince1970)
        let newTask = TaskItem(id: tempId, title: title, category: "general", priority: priority, energyLevel: energyLevel, status: "pending", time: "Just now")
        self.tasks.insert(newTask, at: 0)
        
        Task {
            let serverId = try? await ClewAPIService.shared.createTask(title: title, priority: priority, energyLevel: energyLevel)
            if let realId = serverId, realId > 0 {
                if let index = self.tasks.firstIndex(where: { $0.id == tempId }) {
                    self.tasks[index] = TaskItem(id: realId, title: title, category: "general", priority: priority, energyLevel: energyLevel, status: "pending", time: "Just now")
                }
            }
        }
    }
    
    func sendChatMessage() async {
        let text = draftPrompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        
        let userMsg = ChatMessage(speaker: .user, content: text)
        self.chatMessages.append(userMsg)
        self.draftPrompt = ""
        
        let agentMsgId = UUID().uuidString
        let agentMsg = ChatMessage(id: agentMsgId, speaker: .agent, content: "")
        self.chatMessages.append(agentMsg)
        
        do {
            let stream = ClewAPIService.shared.streamPrompt(text)
            var streamedContent = ""
            for try await token in stream {
                streamedContent += token
                if let index = self.chatMessages.firstIndex(where: { $0.id == agentMsgId }) {
                    self.chatMessages[index] = ChatMessage(
                        id: agentMsgId,
                        speaker: .agent,
                        content: streamedContent,
                        timestamp: Date(),
                        source: "mobile_native"
                    )
                }
            }
        } catch {
            let errorMsg = ChatMessage(speaker: .system, content: "Error connecting to Clew Brain stream: \(error.localizedDescription)")
            self.chatMessages.append(errorMsg)
        }
    }
}
