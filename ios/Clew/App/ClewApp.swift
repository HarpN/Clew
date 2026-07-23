import SwiftUI

@main
struct ClewApp: App {
    @StateObject private var briefViewModel = DailyBriefViewModel()
    @StateObject private var voiceManager = LiveKitVoiceManager()

    var body: some Scene {
        WindowGroup {
            NavigationSplitView {
                MainSidebarView()
            } detail: {
                DailyBriefView()
                    .environmentObject(briefViewModel)
                    .environmentObject(voiceManager)
            }
            .preferredColorScheme(.dark)
        }
    }
}
