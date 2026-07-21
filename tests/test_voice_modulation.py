"""
tests/test_voice_modulation.py - Unit test suite for voice modulation mapping and punctuation damping.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from agent.agent import resolve_voice_synthesis_options, make_custom_tts

class TestVoiceModulation(unittest.TestCase):
    def test_coordinate_mapping(self):
        # 1. Warm Peer Centroid: {"x": 0.5, "y": 0.5}
        # WPM: 165 - (0.5 * 25) = 152
        # speed: 152 / 165.0 = 0.92
        # Temp: 0.6
        opts_warm = resolve_voice_synthesis_options({"x": 0.5, "y": 0.5})
        self.assertAlmostEqual(opts_warm["speed"], 0.92, places=2)
        self.assertAlmostEqual(opts_warm["temperature"], 0.6, places=2)

        # 2. Dry Analyst Centroid: {"x": -0.5, "y": -0.5}
        # WPM: 165 - (-0.5 * 25) = 177
        # speed: 177 / 165.0 = 1.07
        # Temp: 0.15
        opts_dry = resolve_voice_synthesis_options({"x": -0.5, "y": -0.5})
        self.assertAlmostEqual(opts_dry["speed"], 1.07, places=2)
        self.assertAlmostEqual(opts_dry["temperature"], 0.15, places=2)

        # 3. Socratic Teacher Centroid: {"x": -0.5, "y": 0.5}
        # Temp: 0.4
        opts_soc = resolve_voice_synthesis_options({"x": -0.5, "y": 0.5})
        self.assertAlmostEqual(opts_soc["speed"], 0.92, places=2)
        self.assertAlmostEqual(opts_soc["temperature"], 0.4, places=2)

        # 4. Blunt Critic Centroid: {"x": 0.5, "y": -0.5}
        # Temp: 0.3
        opts_critic = resolve_voice_synthesis_options({"x": 0.5, "y": -0.5})
        self.assertAlmostEqual(opts_critic["speed"], 1.07, places=2)
        self.assertAlmostEqual(opts_critic["temperature"], 0.3, places=2)

    def test_punctuation_damping_under_threshold(self):
        # y = -0.5 < -0.3: Commas should be stripped
        mock_tts = MagicMock()
        mock_syn = MagicMock(return_value="audio_chunk")
        mock_tts.synthesize = mock_syn
        
        # Mock stream push_text
        mock_stream = MagicMock()
        mock_push = MagicMock()
        mock_stream.push_text = mock_push
        mock_tts.stream = MagicMock(return_value=mock_stream)
        
        # Wrap TTS
        wrapped_tts = make_custom_tts(mock_tts, y_val=-0.5)
        
        # Test synthesize
        wrapped_tts.synthesize("Hello, this is a test, with commas.")
        mock_syn.assert_called_once_with("Hello this is a test with commas.")
        
        # Test stream push_text
        stream = wrapped_tts.stream()
        stream.push_text("One, two, three")
        mock_push.assert_called_once_with("One two three")

    def test_punctuation_damping_above_threshold(self):
        # y = 0.5 >= -0.3: Commas should NOT be stripped
        mock_tts = MagicMock()
        mock_syn = MagicMock(return_value="audio_chunk")
        mock_tts.synthesize = mock_syn
        
        # Test synthesize
        wrapped_tts = make_custom_tts(mock_tts, y_val=0.5)
        wrapped_tts.synthesize("Hello, this is a test, with commas.")
        mock_syn.assert_called_once_with("Hello, this is a test, with commas.")

if __name__ == "__main__":
    unittest.main()
