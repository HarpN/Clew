import SwiftUI

struct LimbicCompassView: View {
    @Binding var limbicState: LimbicState
    var interactive: Bool = true
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: "brain.head.profile")
                    .foregroundColor(.purple)
                Text("Limbic Compass Vector")
                    .font(.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                
                Spacer()
                
                Text(limbicState.activeMood)
                    .font(.caption)
                    .fontWeight(.medium)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(Color.purple.opacity(0.25)))
                    .foregroundColor(.purple)
            }
            
            // 2D Compass Grid Canvas
            GeometryReader { geo in
                let width = geo.size.width
                let height = geo.size.height
                let point = limbicState.unitPoint
                let posX = point.x * width
                let posY = point.y * height
                
                ZStack {
                    // Outer border background
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color.black.opacity(0.4))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(Color.purple.opacity(0.3), lineWidth: 1)
                        )
                    
                    // Axis Lines
                    Path { path in
                        // Vertical Axis (Arousal)
                        path.move(to: CGPoint(x: width / 2, y: 0))
                        path.addLine(to: CGPoint(x: width / 2, y: height))
                        
                        // Horizontal Axis (Valence)
                        path.move(to: CGPoint(x: 0, y: height / 2))
                        path.addLine(to: CGPoint(x: width, y: height / 2))
                    }
                    .stroke(Color.white.opacity(0.15), style: StrokeStyle(lineWidth: 1, dash: [4, 4]))
                    
                    // Quadrant Labels
                    Group {
                        Text("HIGH AROUSAL")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(.gray.opacity(0.6))
                            .position(x: width / 2, y: 12)
                        
                        Text("LOW AROUSAL")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(.gray.opacity(0.6))
                            .position(x: width / 2, y: height - 12)
                        
                        Text("NEG")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(.gray.opacity(0.6))
                            .position(x: 16, y: height / 2)
                        
                        Text("POS")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(.gray.opacity(0.6))
                            .position(x: width - 16, y: height / 2)
                    }
                    
                    // Active Mood Marker Node
                    Circle()
                        .fill(
                            RadialGradient(
                                gradient: Gradient(colors: [.cyan, .purple]),
                                center: .center,
                                startRadius: 2,
                                endRadius: 16
                            )
                        )
                        .frame(width: 24, height: 24)
                        .shadow(color: .purple, radius: 8)
                        .overlay(Circle().stroke(Color.white, lineWidth: 2))
                        .position(x: posX, y: posY)
                }
                .gesture(
                    DragGesture(minimumDistance: 0)
                        .onChanged { value in
                            guard interactive else { return }
                            let rawX = max(0, min(width, value.location.x))
                            let rawY = max(0, min(height, value.location.y))
                            
                            let v = (rawX / width) * 2.0 - 1.0
                            let a = 1.0 - (rawY / height) * 2.0
                            
                            self.limbicState.valence = v
                            self.limbicState.arousal = a
                            self.limbicState.activeMood = self.limbicState.quadrantName
                        }
                )
            }
            .frame(height: 140)
            
            // Vector Coordinates Footer
            HStack {
                Text(String(format: "Valence: %.2f", limbicState.valence))
                Spacer()
                Text(String(format: "Arousal: %.2f", limbicState.arousal))
                Spacer()
                Text(String(format: "Dominance: %.2f", limbicState.dominance))
            }
            .font(.system(size: 10, weight: .semibold, design: .monospaced))
            .foregroundColor(.gray)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color(white: 0.1).opacity(0.7))
        )
    }
}
