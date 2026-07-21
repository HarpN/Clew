"""
tests/test_amygdala.py - Unit and integration tests for the Amygdala Real-Time Friction Engine.
"""

import sys
import os
import unittest
import asyncio
import uuid
from unittest.mock import patch, MagicMock

# Ensure root workspace is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
from neuromorphic_subsystems import Amygdala
from brain_orchestrator import CognitiveBrain

class TestAmygdalaFrictionEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()

    def test_01_sentiment_lexical_analysis(self):
        amygdala = Amygdala()
        
        # Stressed / Negative input
        stressed_score = amygdala.analyze_sentiment("No! Stop! That is completely wrong!")
        self.assertLess(stressed_score, 0.0)
        self.assertEqual(stressed_score, -1.0) # check clamping/limits
        
        # Positive / Calm input
        calm_score = amygdala.analyze_sentiment("Yes, this is great thanks!")
        self.assertGreater(calm_score, 0.0)
        
        # Empty input
        empty_score = amygdala.analyze_sentiment("")
        self.assertEqual(empty_score, 0.0)

    def test_02_friction_calculation_low_stress(self):
        amygdala = Amygdala(stress_threshold=0.75)
        # Slow typing, positive sentiment, no repetition
        f_score = amygdala.calculate_friction(
            keystroke_deltas=[12.0],
            recent_prompts=["hello", "how are you"],
            sentiment_score=0.8
        )
        self.assertLess(f_score, 0.75)
        self.assertFalse(amygdala.should_shunt_to_terse(f_score))

    def test_03_friction_calculation_high_stress(self):
        amygdala = Amygdala(stress_threshold=0.75)
        # Rapid typing (stressed cadence), exclamation spam, negative sentiment, repetitive inputs
        f_score = amygdala.calculate_friction(
            keystroke_deltas=[0.5],
            recent_prompts=["wrong", "wrong", "No! Stop! That is completely wrong!"],
            sentiment_score=-1.0
        )
        self.assertGreaterEqual(f_score, 0.75)
        self.assertTrue(amygdala.should_shunt_to_terse(f_score))

    @patch('broca_translator.ModelRouter.execute_streaming_completion')
    @patch('brain_orchestrator.ModelRouter.classify_intent')
    def test_04_cognitive_brain_shunts_to_terse(self, mock_classify, mock_stream):
        from protocol import IntentCommand, Domain, ActionType
        
        # Mock intent classification to return CHITCHAT to bypass DB command execution
        mock_classify.return_value = IntentCommand(
            domain=Domain.CHITCHAT,
            action=ActionType.CHITCHAT,
            confidence=1.0,
            reasoning="Mocked chitchat intent to isolate integration testing",
            payload={"message": "No! Stop! That is completely wrong!"},
            command_id=str(uuid.uuid4())
        )

        # Mock the stream generator response
        async def mock_async_gen(*args, **kwargs):
            yield "0"
            
        mock_stream.return_value = mock_async_gen()

        brain = CognitiveBrain()
        
        # Call process_thought_cycle with high stress metrics to trigger Terse Mode
        is_success, friendly_res, intent, coords = asyncio.run(
            brain.process_thought_cycle(
                user_prompt="No! Stop! That is completely wrong!",
                goal_tether_id="goal_tether_chores",
                keystroke_deltas=[0.3]
            )
        )
        
        self.assertTrue(is_success)
        self.assertTrue(brain.terse_mode_active)

        # Consume the generator to run the body of compile_response_stream
        async def consume_generator():
            chunks = []
            async for chunk in friendly_res:
                chunks.append(chunk)
            return "".join(chunks)
            
        response_text = asyncio.run(consume_generator())
        self.assertEqual(response_text, "0")
        
        # Verify the streaming execution was called with max_tokens cap and the Terse system prompt
        mock_stream.assert_called_once()
        called_kwargs = mock_stream.call_args[1]
        
        self.assertIn("You are operating in safe Terse Mode.", called_kwargs["system_prompt"])
        self.assertEqual(called_kwargs["options"]["num_predict"], 64)
        self.assertEqual(called_kwargs["options"]["max_tokens"], 64)

if __name__ == "__main__":
    unittest.main()
