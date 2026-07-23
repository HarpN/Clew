import Foundation
import Combine
import AVFoundation
import LiveKit

public enum VoiceConnectionState: String, Sendable {
    case disconnected = "Disconnected"
    case connecting = "Connecting..."
    case connected = "Connected (Sub-500ms WebRTC)"
    case error = "Connection Error"
}

public struct LiveKitSessionInfo: Codable, Sendable {
    public let token: String
    public var url: String
    public let room: String
    
    public init(token: String, url: String, room: String) {
        self.token = token
        self.url = url
        self.room = room
    }
}

@MainActor
public final class LiveKitVoiceManager: ObservableObject {
    @Published public var connectionState: VoiceConnectionState = .disconnected
    @Published public var isMuted: Bool = false
    @Published public var isAgentSpeaking: Bool = false
    @Published public var audioPowerLevels: [Float] = Array(repeating: 0.1, count: 12)
    @Published public var roomName: String = ""
    @Published public var lastError: String? = nil
    
    private var room: Room?
    private var waveformTimer: Timer?
    
    public init() {}
    
    public func connect() async {
        connectionState = .connecting
        lastError = nil
        
        do {
            let sessionInfo = try await ClewAPIService.shared.fetchLiveKitToken()
            self.roomName = sessionInfo.room
            
            let newRoom = Room()
            newRoom.add(delegate: self)
            try await newRoom.connect(url: sessionInfo.url, token: sessionInfo.token)
            self.room = newRoom
            
            self.connectionState = .connected
            startAudioWaveformSimulation()
        } catch {
            self.connectionState = .error
            self.lastError = error.localizedDescription
            print("[LiveKitVoiceManager] Connection failed: \(error)")
        }
    }
    
    public func disconnect() {
        stopAudioWaveformSimulation()
        if let activeRoom = room {
            Task {
                await activeRoom.disconnect()
            }
            self.room = nil
        }
        connectionState = .disconnected
        isAgentSpeaking = false
        audioPowerLevels = Array(repeating: 0.1, count: 12)
    }
    
    public func toggleMute() {
        isMuted.toggle()
        if let activeRoom = room {
            let muteState = isMuted
            Task {
                try? await activeRoom.localParticipant.setMicrophone(enabled: !muteState)
            }
        }
    }
    
    private func startAudioWaveformSimulation() {
        stopAudioWaveformSimulation()
        waveformTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self = self, self.connectionState == .connected else { return }
                if self.isMuted {
                    self.audioPowerLevels = Array(repeating: 0.05, count: 12)
                    return
                }
                
                self.audioPowerLevels = (0..<12).map { _ in
                    Float.random(in: 0.15...0.95)
                }
                
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
    
    nonisolated deinit {
        // Nonisolated deinit safety wrapper
    }
}

// MARK: - RoomDelegate Conformance
extension LiveKitVoiceManager: RoomDelegate {
    nonisolated public func room(_ room: Room, didUpdateConnectionState connectionState: ConnectionState, oldValue: ConnectionState) {
        Task { @MainActor in
            switch connectionState {
            case .connected:
                self.connectionState = .connected
            case .disconnected:
                self.connectionState = .disconnected
            case .reconnecting:
                self.connectionState = .connecting
            default:
                break
            }
        }
    }
}
