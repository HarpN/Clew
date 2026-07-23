import SwiftUI

struct CollapsibleTowerCard<Content: View>: View {
    let title: String
    let icon: String
    let badgeCount: Int
    @Binding var isExpanded: Bool
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(spacing: 0) {
            // Header Bar
            Button(action: {
                withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                    isExpanded.toggle()
                }
            }) {
                HStack {
                    Image(systemName: icon)
                        .font(.title3)
                        .foregroundColor(.cyan)
                        .frame(width: 28)

                    Text(title)
                        .font(.headline)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)

                    Spacer()

                    if badgeCount > 0 {
                        Text("\(badgeCount)")
                            .font(.caption)
                            .fontWeight(.bold)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Capsule().fill(Color.cyan.opacity(0.2)))
                            .foregroundColor(.cyan)
                    }

                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .font(.subheadline)
                        .foregroundColor(.gray)
                        .padding(.leading, 4)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 14)
                .background(
                    RoundedRectangle(cornerRadius: 14)
                        .fill(Color(white: 0.12).opacity(0.8))
                        .overlay(
                            RoundedRectangle(cornerRadius: 14)
                                .stroke(Color.white.opacity(0.08), lineWidth: 1)
                        )
                )
            }
            .buttonStyle(PlainButtonStyle())

            // Expandable Body
            if isExpanded {
                VStack(spacing: 10) {
                    content()
                }
                .padding(14)
                .background(
                    RoundedRectangle(cornerRadius: 14)
                        .fill(Color(white: 0.08).opacity(0.6))
                )
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }
}
