import SwiftUI

struct MainSidebarView: View {
    @EnvironmentObject private var briefViewModel: DailyBriefViewModel
    @EnvironmentObject private var voiceManager: LiveKitVoiceManager
    @EnvironmentObject private var environment: AppEnvironment

    var body: some View {
        List {
            Section(header: Text("Core Engine").font(.caption).foregroundColor(.gray)) {
                NavigationLink(destination: DailyBriefView()) {
                    Label("Daily Executive Brief", systemImage: "building.2.crop.circle.fill")
                        .foregroundColor(.white)
                }

                NavigationLink(destination: VoiceRoomView()) {
                    HStack {
                        Label("WebRTC Voice Hub", systemImage: "waveform.circle.fill")
                            .foregroundColor(.white)
                        Spacer()
                        Circle()
                            .fill(voiceManager.connectionState == .connected ? Color.green : Color.orange)
                            .frame(width: 8, height: 8)
                    }
                }
            }

            Section(header: Text("Subsystems").font(.caption).foregroundColor(.gray)) {
                NavigationLink(destination: TelemetryView()) {
                    Label("Telemetry & Micro-Agent", systemImage: "cpu.fill")
                        .foregroundColor(.white)
                }

                NavigationLink(destination: MemoryGraphView()) {
                    Label("Memory Graph", systemImage: "point.3.connected.trianglepath.dotted")
                        .foregroundColor(.white)
                }
            }

            Section(header: Text("Network & Gateway").font(.caption).foregroundColor(.gray)) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Tailscale / Local Base URL")
                        .font(.caption2)
                        .foregroundColor(.gray)
                    Text(environment.baseURL)
                        .font(.system(size: 11, weight: .semibold, design: .monospaced))
                        .foregroundColor(.cyan)
                }
                .padding(.vertical, 4)
            }
        }
        .listStyle(SidebarListStyle())
        .navigationTitle("Clew V5")
    }
}

// Supporting view stubs for navigation targets
struct VoiceRoomView: View {
    @EnvironmentObject private var voiceManager: LiveKitVoiceManager

    var body: some View {
        VStack(spacing: 20) {
            Text("Sub-500ms WebRTC Voice Room")
                .font(.title2)
                .fontWeight(.bold)

            Text("Status: \(voiceManager.connectionState.rawValue)")
                .font(.subheadline)
                .foregroundColor(.cyan)

            AudioWaveformView(
                powerLevels: voiceManager.audioPowerLevels,
                isSpeaking: voiceManager.isAgentSpeaking
            )

            HStack(spacing: 20) {
                Button(action: {
                    Task {
                        if voiceManager.connectionState == .connected {
                            voiceManager.disconnect()
                        } else {
                            await voiceManager.connect()
                        }
                    }
                }) {
                    Label(
                        voiceManager.connectionState == .connected ? "Disconnect" : "Connect Voice",
                        systemImage: voiceManager.connectionState == .connected ? "phone.down.fill" : "phone.fill"
                    )
                    .padding()
                    .background(voiceManager.connectionState == .connected ? Color.red : Color.green)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }

                Button(action: {
                    voiceManager.toggleMute()
                }) {
                    Image(systemName: voiceManager.isMuted ? "mic.slash.fill" : "mic.fill")
                        .padding()
                        .background(Color.gray.opacity(0.3))
                        .foregroundColor(.white)
                        .clipShape(Circle())
                }
            }
        }
        .padding()
        .navigationTitle("Voice Engine")
    }
}

struct TelemetryView: View {
    var body: some View {
        VStack(spacing: 12) {
            Text("Engine Telemetry & Health")
                .font(.title3)
                .bold()
            Text("FastAPI Proxy / Dual-Stage Brain Orchestrator v5")
                .font(.caption)
                .foregroundColor(.gray)
            Spacer()
        }
        .padding()
        .navigationTitle("Telemetry")
    }
}

struct MemoryGraphView: View {
    var body: some View {
        VStack(spacing: 12) {
            Text("Graph Memory Entity Matrix")
                .font(.title3)
                .bold()
            Spacer()
        }
        .padding()
        .navigationTitle("Memory Graph")
    }
}
