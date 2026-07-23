import Foundation
import Combine

@MainActor
final class VoiceSessionViewModel: ObservableObject {
    @Published var latencyMs: Int = 340
    @Published var activeCodec: String = "Opus 48kHz"
    @Published var transcripts: [ChatMessage] = []
    @Published var isRecording: Bool = false
    
    func addTranscript(speaker: MessageSpeaker, text: String) {
        let msg = ChatMessage(speaker: speaker, content: text, source: "webrtc_voice")
        transcripts.append(msg)
    }
    
    func clearTranscripts() {
        transcripts.removeAll()
    }
}
