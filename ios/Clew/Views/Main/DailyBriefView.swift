import SwiftUI

public struct DailyBriefView: View {
    @EnvironmentObject private var briefViewModel: DailyBriefViewModel
    @EnvironmentObject private var voiceManager: LiveKitVoiceManager
    @State private var newTaskTitle: String = ""

    public init() {}

    public var body: some View {
        VStack(spacing: 0) {
            // Header Bar
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Executive Daily Brief")
                        .font(.title2)
                        .fontWeight(.bold)
                    Text("Lakeland, FL • Clew V5 Engine")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                Spacer()
                
                // Voice Session Status Indicator
                HStack(spacing: 6) {
                    Circle()
                        .fill(voiceManager.connectionState == .connected ? Color.green : Color.orange)
                        .frame(width: 8, height: 8)
                    Text(voiceManager.connectionState.rawValue)
                        .font(.caption2)
                        .monospaced()
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(Color.secondary.opacity(0.15))
                .cornerRadius(12)
            }
            .padding()

            Divider()

            // Executive Towers
            ScrollView {
                VStack(spacing: 16) {
                    // Task Tower
                    DisclosureGroup("Today's Focus (\(briefViewModel.tasks.count))", isExpanded: $briefViewModel.isTasksTowerExpanded) {
                        VStack(spacing: 8) {
                            ForEach(briefViewModel.tasks) { task in
                                HStack {
                                    Button(action: {
                                        briefViewModel.resolveTask(id: task.id)
                                    }) {
                                        Image(systemName: "circle")
                                            .foregroundColor(.indigo)
                                    }
                                    
                                    VStack(alignment: .leading) {
                                        Text(task.title)
                                            .font(.subheadline)
                                            .fontWeight(.medium)
                                        Text("\(task.category.capitalized) • \(task.priority.rawValue) • \(task.energyLevel.rawValue) energy")
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                    }
                                    Spacer()
                                }
                                .padding(10)
                                .background(Color.secondary.opacity(0.1))
                                .cornerRadius(8)
                            }
                        }
                        .padding(.top, 8)
                    }
                    .padding()
                    .background(Color.secondary.opacity(0.08))
                    .cornerRadius(12)
                }
                .padding()
            }

            Spacer()

            // Quick Capture Input Bar
            HStack {
                TextField("Add task or ask Clew...", text: $newTaskTitle)
                    .textFieldStyle(.roundedBorder)
                
                Button(action: {
                    guard !newTaskTitle.trimmingCharacters(in: .whitespaces).isEmpty else { return }
                    briefViewModel.addTask(title: newTaskTitle)
                    newTaskTitle = ""
                }) {
                    Image(systemName: "paperplane.fill")
                        .padding(8)
                        .background(Color.indigo)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
            }
            .padding()
        }
        .task {
            await briefViewModel.loadState()
        }
    }
}
