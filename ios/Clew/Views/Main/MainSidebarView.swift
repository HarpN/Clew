import SwiftUI

public struct MainSidebarView: View {
    @State private var selectedTab: String = "today"
    
    public init() {}
    
    public var body: some View {
        List {
            Section("Command Center") {
                NavigationLink(value: "today") {
                    Label("Today's Focus", systemImage: "sun.max.fill")
                }
                NavigationLink(value: "calendar") {
                    Label("Schedule & White Space", systemImage: "calendar")
                }
                NavigationLink(value: "logistics") {
                    Label("Proactive Logistics", systemImage: "shippingbox.fill")
                }
            }
            
            Section("Memory & Engine") {
                NavigationLink(value: "memory") {
                    Label("Learned Habits", systemImage: "brain.head.profile")
                }
                NavigationLink(value: "telemetry") {
                    Label("Engine Telemetry", systemImage: "cpu")
                }
            }
        }
        .navigationTitle("Clew V5")
    }
}
