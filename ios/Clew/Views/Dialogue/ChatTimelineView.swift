import SwiftUI

struct ChatTimelineView: View {
    let messages: [String]
    
    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 12) {
                    ForEach(Array(messages.enumerated()), id: \.offset) { index, msg in
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(msg)
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
                        .id(index)
                    }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
            }
            .onChange(of: messages.count) { _ in
                if !messages.isEmpty {
                    withAnimation {
                        proxy.scrollTo(messages.count - 1, anchor: .bottom)
                    }
                }
            }
        }
    }
}
