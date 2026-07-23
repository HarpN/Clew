import Foundation
import CoreGraphics

/// 2D Limbic Mood Coordinates and Quadrant Representation
struct LimbicState: Codable, Equatable {
    var valence: Double    // -1.0 (negative) to +1.0 (positive)
    var arousal: Double    // -1.0 (calm) to +1.0 (excited/stressed)
    var dominance: Double  // -1.0 (submissive) to +1.0 (dominant)
    var activeMood: String
    
    init(
        valence: Double = 0.2,
        arousal: Double = 0.1,
        dominance: Double = 0.5,
        activeMood: String = "Analytical Neutral"
    ) {
        self.valence = max(-1.0, min(1.0, valence))
        self.arousal = max(-1.0, min(1.0, arousal))
        self.dominance = max(-1.0, min(1.0, dominance))
        self.activeMood = activeMood
    }
    
    /// Normalized point mapped to unit range [0, 1] for UI plotting inside a 2D compass view
    var unitPoint: CGPoint {
        CGPoint(
            x: (valence + 1.0) / 2.0,
            y: (1.0 - arousal) / 2.0  // Invert y so positive arousal is top
        )
    }
    
    var quadrantName: String {
        switch (valence >= 0, arousal >= 0) {
        case (true, true): return "Focused High Energy"
        case (true, false): return "Calm & Reflective"
        case (false, true): return "High Stress / Vigilant"
        case (false, false): return "Depleted / Low Drive"
        }
    }
}
