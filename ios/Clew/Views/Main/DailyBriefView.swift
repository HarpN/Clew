import SwiftUI

struct DailyBriefView: View {
    @EnvironmentObject private var briefViewModel: DailyBriefViewModel
    @EnvironmentObject private var voiceManager: LiveKitVoiceManager
    
    @State private var showingAddTaskSheet: Bool = false
    @State private var newTaskTitle: String = ""
    @State private var selectedPriority: TaskPriority = .p2
    @State private var selectedEnergy: EnergyLevel = .medium

    var body: some View {
        VStack(spacing: 0) {
            // Header Banner
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Executive Tower")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.white)

                    Text(briefViewModel.statusMessage)
                        .font(.caption)
                        .foregroundColor(briefViewModel.isLoading ? .yellow : .gray)
                }

                Spacer()

                // Voice Quick-Connect Button & Indicator
                if voiceManager.connectionState == .connected {
                    AudioWaveformView(
                        powerLevels: voiceManager.audioPowerLevels,
                        isSpeaking: voiceManager.isAgentSpeaking
                    )
                }

                Button(action: {
                    Task {
                        if voiceManager.connectionState == .connected {
                            voiceManager.disconnect()
                        } else {
                            await voiceManager.connect()
                        }
                    }
                }) {
                    Image(systemName: voiceManager.connectionState == .connected ? "waveform.path.badge.minus" : "waveform.path.badge.plus")
                        .font(.title3)
                        .padding(10)
                        .background(
                            Circle()
                                .fill(voiceManager.connectionState == .connected ? Color.cyan.opacity(0.3) : Color.gray.opacity(0.2))
                        )
                        .foregroundColor(voiceManager.connectionState == .connected ? .cyan : .white)
                }

                Button(action: {
                    Task {
                        await briefViewModel.loadState()
                    }
                }) {
                    Image(systemName: "arrow.clockwise")
                        .font(.title3)
                        .padding(10)
                        .background(Circle().fill(Color.gray.opacity(0.2)))
                        .foregroundColor(.white)
                }
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)
            .padding(.bottom, 8)

            ScrollView {
                VStack(spacing: 16) {
                    // 2D Limbic Mood Compass Widget
                    LimbicCompassView(limbicState: $briefViewModel.limbicState)

                    // Collapsible Tower 1: Active Tasks Tower
                    CollapsibleTowerCard(
                        title: "Active Tasks Tower",
                        icon: "checkmark.square.stack.fill",
                        badgeCount: briefViewModel.tasks.count,
                        isExpanded: $briefViewModel.isTasksTowerExpanded
                    ) {
                        HStack {
                            Text("WORKING STATE TASKS")
                                .font(.caption2)
                                .fontWeight(.bold)
                                .foregroundColor(.gray)

                            Spacer()

                            Button(action: { showingAddTaskSheet = true }) {
                                Label("Add Task", systemImage: "plus")
                                    .font(.caption)
                                    .foregroundColor(.cyan)
                            }
                        }

                        if briefViewModel.tasks.isEmpty {
                            Text("No pending tasks in working state")
                                .font(.subheadline)
                                .foregroundColor(.gray)
                                .padding(.vertical, 12)
                        } else {
                            ForEach(briefViewModel.tasks) { task in
                                TaskRowView(task: task) {
                                    withAnimation {
                                        briefViewModel.resolveTask(id: task.id)
                                    }
                                }
                            }
                        }
                    }

                    // Collapsible Tower 2: Strategic Projects Tower
                    CollapsibleTowerCard(
                        title: "Strategic Projects",
                        icon: "folder.fill",
                        badgeCount: 2,
                        isExpanded: $briefViewModel.isProjectsTowerExpanded
                    ) {
                        VStack(alignment: .leading, spacing: 8) {
                            ProjectItemRow(title: "Clew V5 Native iOS Integration", status: "Active Sprint", progress: 0.85)
                            ProjectItemRow(title: "Prefrontal Dual-Stage Engine Optimization", status: "In Progress", progress: 0.60)
                        }
                    }

                    // Collapsible Tower 3: System Calendar & Cron Schedule
                    CollapsibleTowerCard(
                        title: "Schedule & Cron Operations",
                        icon: "clock.fill",
                        badgeCount: 1,
                        isExpanded: $briefViewModel.isCalendarTowerExpanded
                    ) {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Image(systemName: "moon.stars.fill").foregroundColor(.purple)
                                Text("Nightly Distillation Cron").font(.subheadline).foregroundColor(.white)
                                Spacer()
                                Text("02:00 AM UTC").font(.caption).foregroundColor(.gray)
                            }
                        }
                    }

                    // Active Chat & Voice Dialogue Timeline Stream
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Image(systemName: "bubble.left.and.bubble.right.fill")
                                .foregroundColor(.cyan)
                            Text("Dialogue Stream")
                                .font(.headline)
                                .foregroundColor(.white)
                        }

                        ChatTimelineView(messages: briefViewModel.chatMessages)
                            .frame(height: 180)
                            .background(
                                RoundedRectangle(cornerRadius: 14)
                                    .fill(Color(white: 0.08).opacity(0.8))
                            )

                        // Message Input Field
                        HStack {
                            TextField("Ask Clew or send command...", text: $briefViewModel.draftPrompt)
                                .padding(12)
                                .background(RoundedRectangle(cornerRadius: 12).fill(Color(white: 0.14)))
                                .foregroundColor(.white)
                                .onSubmit {
                                    Task {
                                        await briefViewModel.sendChatMessage()
                                    }
                                }

                            Button(action: {
                                Task {
                                    await briefViewModel.sendChatMessage()
                                }
                            }) {
                                Image(systemName: "paperplane.fill")
                                    .foregroundColor(.white)
                                    .padding(12)
                                    .background(Circle().fill(Color.blue))
                            }
                        }
                    }
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 24)
            }
        }
        .background(Color.black.edgesIgnoringSafeArea(.all))
        .navigationTitle("Daily Brief")
        .task {
            await briefViewModel.loadState()
        }
        .sheet(isPresented: $showingAddTaskSheet) {
            AddTaskSheetView(
                title: $newTaskTitle,
                priority: $selectedPriority,
                energy: $selectedEnergy
            ) {
                if !newTaskTitle.isEmpty {
                    briefViewModel.addTask(
                        title: newTaskTitle,
                        priority: selectedPriority,
                        energyLevel: selectedEnergy
                    )
                    newTaskTitle = ""
                }
                showingAddTaskSheet = false
            }
        }
    }
}

// Supporting Task Row Subview
struct TaskRowView: View {
    let task: TaskItem
    let onResolve: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Button(action: onResolve) {
                Image(systemName: "circle")
                    .font(.title3)
                    .foregroundColor(.gray)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(task.title)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(.white)

                HStack(spacing: 6) {
                    Text(task.priority.rawValue)
                        .font(.system(size: 9, weight: .bold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Capsule().fill(task.priority == .p1 ? Color.red.opacity(0.3) : Color.orange.opacity(0.3)))
                        .foregroundColor(task.priority == .p1 ? .red : .orange)

                    Image(systemName: task.energyLevel.iconName)
                        .font(.caption2)
                        .foregroundColor(.yellow)

                    Text(task.time)
                        .font(.caption2)
                        .foregroundColor(.gray)
                }
            }

            Spacer()
        }
        .padding(10)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color(white: 0.12))
        )
    }
}

struct ProjectItemRow: View {
    let title: String
    let status: String
    let progress: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(title).font(.subheadline).foregroundColor(.white)
                Spacer()
                Text(status).font(.caption).foregroundColor(.cyan)
            }
            ProgressView(value: progress)
                .tint(.cyan)
        }
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 8).fill(Color(white: 0.12)))
    }
}

struct AddTaskSheetView: View {
    @Binding var title: String
    @Binding var priority: TaskPriority
    @Binding var energy: EnergyLevel
    let onSave: () -> Void

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Task Details")) {
                    TextField("Task Title", text: $title)
                    
                    Picker("Priority", selection: $priority) {
                        ForEach(TaskPriority.allCases, id: \.self) { p in
                            Text(p.rawValue).tag(p)
                        }
                    }
                    
                    Picker("Energy Required", selection: $energy) {
                        ForEach(EnergyLevel.allCases, id: \.self) { e in
                            Text(e.rawValue.capitalized).tag(e)
                        }
                    }
                }
            }
            .navigationTitle("New Working State Task")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save", action: onSave)
                }
            }
        }
    }
}
