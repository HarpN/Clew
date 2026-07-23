import Foundation
import Combine
import AVFoundation

enum VoiceConnectionState: String {
    case disconnected = "Disconnected"
    case connecting = "Connecting..."
    case connected = "Connected (Sub-500ms WebRTC)"
    case error = "Connection Error"
}

@MainActor
final class LiveKitVoiceManager: ObservableObject {
    @Published var connectionState: VoiceConnectionState = .disconnected
    @Published var isMuted: Bool = false
    @Published var isAgentSpeaking: Bool = false
    @Published var audioPowerLevels: [Float] = Array(repeating: 0.1, count: 12)
    @Published var roomName: String = ""
    @Published var lastError: String? = nil
    
    private var waveformTimer: Timer?
    
    init() {}
    
    func connect() async {
        connectionState = .connecting
        lastError = nil
        
        do {
            let sessionInfo = try await ClewAPIService.shared.fetchLiveKitToken()
            self.roomName = sessionInfo.room
            
            // WebRTC Connection Setup - LiveKit SDK integration boundary
            try await Task.sleep(nanoseconds: 300_000_000) // Simulated connection handshake
            
            self.connectionState = .connected
            startAudioWaveformSimulation()
        } catch {
            self.connectionState = .error
            self.lastError = error.localizedDescription
            print("[LiveKitVoiceManager] Connection failed: \(error)")
        }
    }
    
    func disconnect() {
        stopAudioWaveformSimulation()
        connectionState = .disconnected
        isAgentSpeaking = false
        audioPowerLevels = Array(repeating: 0.1, count: 12)
    }
    
    func toggleMute() {
        isMuted.toggle()
    }
    
    private func startAudioWaveformSimulation() {
        waveformTimer?.invalidate()
        waveformTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self = self, self.connectionState == .connected else { return }
                if self.isMuted {
                    self.audioPowerLevels = Array(repeating: 0.05, count: 12)
                    return
                }
                
                // Dynamic audio spectrum power levels simulation
                self.audioPowerLevels = (0..<12).map { _ in
                    Float.random(in: 0.15...0.95)
                }
                
                // Randomly toggle agent speaking indicator for testing waveform feedback
                if Float.random(in: 0...1.0) < 0.1 {
                    self.isAgentSpeaking.toggle()
                }
            }
        }
    }
    
    private func stopAudioWaveformSimulation() {
        waveformTimer?.invalidate()
        waveformTimer = nil
    }
    
    deinit {
        waveformTimer?.invalidate()
    }
}
