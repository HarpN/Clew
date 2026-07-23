import Foundation
import Combine

@MainActor
public final class VoiceSessionViewModel: ObservableObject {
    @Published public var isVoiceActive: Bool = false
    @Published public var statusMessage: String = "Disconnected"
    @Published public var audioPowerLevels: [Float] = Array(repeating: 0.1, count: 12)
    
    private var cancellables = Set<AnyCancellable>()
    private let voiceManager: LiveKitVoiceManager
    
    public init(voiceManager: LiveKitVoiceManager) {
        self.voiceManager = voiceManager
        
        voiceManager.$connectionState
            .map { $0.rawValue }
            .assign(to: \.statusMessage, on: self)
            .store(in: &cancellables)
            
        voiceManager.$audioPowerLevels
            .assign(to: \.audioPowerLevels, on: self)
            .store(in: &cancellables)
    }
    
    public func toggleSession() {
        if isVoiceActive {
            voiceManager.disconnect()
            isVoiceActive = false
        } else {
            Task {
                await voiceManager.connect()
                isVoiceActive = true
            }
        }
    }
}
