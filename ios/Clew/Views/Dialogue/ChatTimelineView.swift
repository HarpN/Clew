import SwiftUI

struct ChatTimelineView: View {
    let messages: [ChatMessage]
    
    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 12) {
                    ForEach(messages) { msg in
                        HStack {
                            if msg.speaker == .user {
                                Spacer(minLength: 40)
                                Text(msg.content)
                                    .font(.subheadline)
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 10)
                                    .background(
                                        RoundedRectangle(cornerRadius: 16)
                                            .fill(Color.blue.opacity(0.8))
                                    )
                                    .foregroundColor(.white)
                            } else {
                                VStack(alignment: .leading, spacing: 4) {
                                    HStack(spacing: 6) {
                                        Image(systemName: msg.speaker == .system ? "gearshape.fill" : "sparkles")
                                            .font(.caption2)
                                            .foregroundColor(.cyan)
                                        Text(msg.speaker == .system ? "SYSTEM" : "CLEW BRAIN")
                                            .font(.system(size: 10, weight: .bold))
                                            .foregroundColor(.gray)
                                    }
                                    
                                    Text(msg.content)
                                        .font(.subheadline)
                                        .foregroundColor(.white)
                                }
                                .padding(.horizontal, 14)
                                .padding(.vertical, 10)
                                .background(
                                    RoundedRectangle(cornerRadius: 16)
                                        .fill(Color(white: 0.14))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 16)
                                                .stroke(Color.white.opacity(0.08), lineWidth: 1)
                                        )
                                )
                                Spacer(minLength: 40)
                            }
                        }
                        .id(msg.id)
                    }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
            }
            .onChange(of: messages.count) { _ in
                if let last = messages.last {
                    withAnimation {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
        }
    }
}
