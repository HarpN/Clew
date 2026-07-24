import SwiftUI

public struct AudioWaveformView: View {
    @EnvironmentObject private var voiceManager: LiveKitVoiceManager
    
    public init() {}
    
    public var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<voiceManager.audioPowerLevels.count, id: \.self) { index in
                let power = voiceManager.audioPowerLevels[index]
                
                Capsule()
                    .fill(voiceManager.connectionState == .connected ? Color.emerald : Color.gray.opacity(0.5))
                    .frame(width: 4, height: max(4, CGFloat(power * 30)))
                    .animation(.spring(response: 0.2, dampingFraction: 0.5), value: power)
            }
        }
        .padding(.vertical, 8)
    }
}

// Custom Emerald color extension to match V5 branding
extension Color {
    static let emerald = Color(red: 16/255, green: 185/255, blue: 129/255)
}
