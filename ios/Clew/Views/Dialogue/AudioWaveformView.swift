import SwiftUI

struct AudioWaveformView: View {
    let powerLevels: [Float]
    let isSpeaking: Bool
    
    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<powerLevels.count, id: \.self) { index in
                let level = CGFloat(powerLevels[index])
                let barHeight = max(6, level * 36)
                
                RoundedRectangle(cornerRadius: 3)
                    .fill(
                        LinearGradient(
                            gradient: Gradient(colors: isSpeaking ? [.cyan, .blue] : [.green, .mint]),
                            startPoint: .bottom,
                            endPoint: .top
                        )
                    )
                    .frame(width: 4, height: barHeight)
                    .animation(.spring(response: 0.15, dampingFraction: 0.5), value: level)
            }
        }
        .frame(height: 40)
        .padding(.horizontal, 12)
        .background(
            Capsule()
                .fill(Color.black.opacity(0.4))
                .overlay(Capsule().stroke(Color.white.opacity(0.1), lineWidth: 1))
        )
    }
}
