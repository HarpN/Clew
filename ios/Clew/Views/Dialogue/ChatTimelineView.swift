import SwiftUI

public struct ChatTimelineView: View {
    @EnvironmentObject private var briefViewModel: DailyBriefViewModel
    @State private var inputText: String = ""
    @State private var isStreaming: Bool = false

    public init() {}

    public var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        ForEach(briefViewModel.chatMessages.indices, id: \.self) { index in
                            let message = briefViewModel.chatMessages[index]
                            let isUser = message.starts(with: "User:")
                            
                            HStack {
                                if isUser { Spacer() }
                                
                                Text(message.replacingOccurrences(of: "User: ", with: "").replacingOccurrences(of: "Clew: ", with: ""))
                                    .font(.subheadline)
                                    .padding(12)
                                    .background(isUser ? Color.indigo.opacity(0.8) : Color.secondary.opacity(0.2))
                                    .foregroundColor(.white)
                                    .cornerRadius(16)
                                
                                if !isUser { Spacer() }
                            }
                            .id(index)
                        }
                    }
                    .padding()
                }
                .onChange(of: briefViewModel.chatMessages.count) {
                    if !briefViewModel.chatMessages.isEmpty {
                        proxy.scrollTo(briefViewModel.chatMessages.count - 1, anchor: .bottom)
                    }
                }
            }
            
            Divider()
            
            HStack {
                TextField("Ask Clew...", text: $inputText)
                    .textFieldStyle(.roundedBorder)
                    .disabled(isStreaming)
                
                Button(action: {
                    Task {
                        await submitPrompt()
                    }
                }) {
                    Image(systemName: isStreaming ? "ellipsis" : "paperplane.fill")
                        .padding(8)
                        .background(isStreaming ? Color.gray : Color.indigo)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
                .disabled(inputText.trimmingCharacters(in: .whitespaces).isEmpty || isStreaming)
            }
            .padding()
        }
    }
    
    private func submitPrompt() async {
        let userText = inputText
        inputText = ""
        briefViewModel.chatMessages.append("User: \(userText)")
        isStreaming = true
        
        do {
            // Add a placeholder for the incoming stream
            briefViewModel.chatMessages.append("Clew: ")
            let streamIndex = briefViewModel.chatMessages.count - 1
            
            let stream = ClewAPIService.shared.streamPrompt(userText)
            for try await token in stream {
                briefViewModel.chatMessages[streamIndex] += token
            }
        } catch {
            briefViewModel.chatMessages.append("Clew: [Connection Error: \(error.localizedDescription)]")
        }
        
        isStreaming = false
    }
}
