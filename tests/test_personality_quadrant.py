"""
tests/test_personality_quadrant.py - Unit test suite for the Limbic Personality Quadrant functionality.
"""
import sys
import os
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from personality_quadrant import PersonalityQuadrant, PERSONALITY_PROFILES
from broca_translator import BrocaArea
from brain_orchestrator import CognitiveBrain

class TestPersonalityQuadrant(unittest.TestCase):
    def test_default_preference(self):
        quad = PersonalityQuadrant()
        self.assertEqual(quad.default_profile, "DRY_ANALYST")
        
        # Test standard resolve
        directives = quad.resolve_limbic_tone("hello", current_friction=0.1)
        self.assertEqual(directives["name"], PERSONALITY_PROFILES["DRY_ANALYST"]["name"])
        self.assertEqual(directives["temperature"], PERSONALITY_PROFILES["DRY_ANALYST"]["base_temperature"])
        self.assertEqual(directives["coordinates"], PERSONALITY_PROFILES["DRY_ANALYST"]["coordinates"])

    def test_linguistic_triggers(self):
        quad = PersonalityQuadrant()
        
        # Blunt critic triggers
        directives = quad.resolve_limbic_tone("be blunt with my code", current_friction=0.1, alpha=1.0)
        self.assertEqual(directives["name"], PERSONALITY_PROFILES["BLUNT_CRITIC"]["name"])
        self.assertEqual(directives["coordinates"], PERSONALITY_PROFILES["BLUNT_CRITIC"]["coordinates"])
        
        # Socratic teacher triggers
        directives = quad.resolve_limbic_tone("teach me how this works", current_friction=0.1, alpha=1.0)
        self.assertEqual(directives["name"], PERSONALITY_PROFILES["SOCRATIC_TEACHER"]["name"])
        self.assertEqual(directives["coordinates"], PERSONALITY_PROFILES["SOCRATIC_TEACHER"]["coordinates"])
        
        # Dry analyst triggers
        directives = quad.resolve_limbic_tone("keep it short", current_friction=0.1, alpha=1.0)
        self.assertEqual(directives["name"], PERSONALITY_PROFILES["DRY_ANALYST"]["name"])
        self.assertEqual(directives["coordinates"], PERSONALITY_PROFILES["DRY_ANALYST"]["coordinates"])
        
        # Warm peer triggers
        directives = quad.resolve_limbic_tone("brainstorm some features with me", current_friction=0.1, alpha=1.0)
        self.assertEqual(directives["name"], PERSONALITY_PROFILES["WARM_PEER"]["name"])
        self.assertEqual(directives["coordinates"], PERSONALITY_PROFILES["WARM_PEER"]["coordinates"])

    def test_friction_shunt(self):
        quad = PersonalityQuadrant()
        # High friction should force DRY_ANALYST
        directives = quad.resolve_limbic_tone("brainstorm some features with me", current_friction=0.8)
        self.assertEqual(directives["name"], PERSONALITY_PROFILES["DRY_ANALYST"]["name"])
        self.assertEqual(directives["override_reason"], "Amygdala Stress Emergency Shunt")
        self.assertEqual(directives["coordinates"], PERSONALITY_PROFILES["DRY_ANALYST"]["coordinates"])

    def test_manual_override(self):
        quad = PersonalityQuadrant()
        # Even with high friction, manual override forces WARM_PEER
        directives = quad.resolve_limbic_tone(
            user_prompt="brainstorm some features with me",
            current_friction=0.8,
            manual_override_key="WARM_PEER"
        )
        self.assertEqual(directives["name"], PERSONALITY_PROFILES["WARM_PEER"]["name"])
        self.assertEqual(directives["override_reason"], "Manual Mood Override")
        self.assertEqual(directives["coordinates"], PERSONALITY_PROFILES["WARM_PEER"]["coordinates"])

    def test_limbic_momentum_ema(self):
        quad = PersonalityQuadrant()
        # Default start: DRY_ANALYST coordinates {"x": -0.5, "y": -0.5}
        self.assertEqual(quad.current_coords, {"x": -0.5, "y": -0.5})
        
        # Transition 1: Target WARM_PEER {"x": 0.5, "y": 0.5} with alpha=0.25
        # x_new = 0.25 * 0.5 + 0.75 * (-0.5) = 0.125 - 0.375 = -0.25
        res = quad.resolve_limbic_tone("brainstorm", current_friction=0.1, alpha=0.25)
        self.assertEqual(res["coordinates"], {"x": -0.25, "y": -0.25})
        
        # Transition 2: Target WARM_PEER {"x": 0.5, "y": 0.5} with alpha=0.25
        # x_new = 0.25 * 0.5 + 0.75 * (-0.25) = 0.125 - 0.1875 = -0.0625 -> round to -0.062
        res2 = quad.resolve_limbic_tone("brainstorm", current_friction=0.1, alpha=0.25)
        self.assertEqual(res2["coordinates"], {"x": -0.062, "y": -0.062})
        
        # Transition 3: Amygdala Stress Emergency Shunt (friction >= 0.75)
        # Should snap instantly to DRY_ANALYST {"x": -0.5, "y": -0.5} (effective_alpha = 1.0)
        res_shunt = quad.resolve_limbic_tone("brainstorm", current_friction=0.8, alpha=0.25)
        self.assertEqual(res_shunt["coordinates"], {"x": -0.5, "y": -0.5})

    def test_broca_override_block(self):
        broca = BrocaArea()
        directives = {
            "name": "Warm Companion",
            "instruction_modifier": "Maintain an encouraging tone.",
            "temperature": 0.6
        }
        prompt = broca._build_system_prompt(terse_mode=False, personality_directives=directives)
        self.assertIn("=== LIMBIC PERSONALITY OVERRIDE ===", prompt)
        self.assertIn("Active Mood: Warm Companion", prompt)
        self.assertIn("Directive: Maintain an encouraging tone.", prompt)

if __name__ == "__main__":
    unittest.main()
