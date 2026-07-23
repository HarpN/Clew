import SwiftUI

@main
struct ClewApp: App {
    @StateObject private var briefViewModel = DailyBriefViewModel()
    @StateObject private var voiceManager = LiveKitVoiceManager()
    @StateObject private var environment = AppEnvironment.shared

    var body: some Scene {
        WindowGroup {
            NavigationSplitView {
                MainSidebarView()
                    .environmentObject(briefViewModel)
                    .environmentObject(voiceManager)
            } detail: {
                DailyBriefView()
                    .environmentObject(briefViewModel)
                    .environmentObject(voiceManager)
            }
            .preferredColorScheme(.dark)
            .environmentObject(environment)
        }
    }
}
