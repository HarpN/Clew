"""
tests/test_broca.py - Unit test suite for Broca's Area translation and styling layer.
"""
import sys
import os
import unittest
import asyncio
from unittest.mock import patch

# Ensure root workspace is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from personality_validator import PersonalityValidator
from persona_manager import PersonaRegistry
from broca_translator import BrocaArea

class TestBrocaTranslator(unittest.TestCase):
    def test_personality_validator_preamble(self):
        text = "Sure! Here is the list of tasks."
        cleaned = PersonalityValidator.clean(text)
        self.assertEqual(cleaned, "the list of tasks.")

    def test_personality_validator_sycophancy(self):
        text = "I'd be happy to help. You made a great choice!"
        cleaned = PersonalityValidator.clean(text)
        self.assertEqual(cleaned, ".") # Since preambles and sycophancy are stripped/replaced with dot or empty

    def test_personality_validator_exclamations(self):
        text = "Clean the kitchen!"
        cleaned = PersonalityValidator.clean(text)
        self.assertEqual(cleaned, "Clean the kitchen.")

    def test_persona_registry(self):
        PersonaRegistry.set_active_persona("professional")
        self.assertIn("professional project coordinator", PersonaRegistry.get_active_persona())
        PersonaRegistry.set_active_persona("default")

    def test_cosine_distance_aligned(self):
        broca = BrocaArea()
        payload = {"task_id": 12, "title": "Buy groceries"}
        response = "I have successfully added the task: Buy groceries with ID 12."
        distance = broca.compute_semantic_distance(response, payload)
        # Highly aligned, so distance should be low (< 0.6)
        self.assertLess(distance, 0.6)

    def test_cosine_distance_diverged(self):
        broca = BrocaArea()
        payload = {"task_id": 12, "title": "Buy groceries"}
        response = "Hello. It is a nice day. How can I help you today?"
        distance = broca.compute_semantic_distance(response, payload)
        # Completely diverged, so distance should be high (>= 0.6)
        self.assertGreaterEqual(distance, 0.6)

    @patch('broca_translator.query_ollama_chat')
    def test_compile_response_success(self, mock_query):
        broca = BrocaArea()
        mock_query.return_value = "Added task Buy groceries with ID 12."
        
        payload = {"task_id": 12, "title": "Buy groceries"}
        res = asyncio.run(broca.compile_response(payload, epsilon=0.6))
        self.assertEqual(res, "Added task Buy groceries with ID 12.")

    @patch('broca_translator.query_ollama_chat')
    def test_compile_response_divergence_check(self, mock_query):
        broca = BrocaArea()
        mock_query.return_value = "Something completely unrelated."
        
        payload = {"task_id": 12, "title": "Buy groceries"}
        with self.assertRaises(ValueError):
            asyncio.run(broca.compile_response(payload, epsilon=0.6))

    @patch('broca_translator.ModelRouter.execute_streaming_completion')
    def test_compile_response_stream_success(self, mock_stream):
        broca = BrocaArea()
        
        # Mock async generator
        async def mock_async_gen(*args, **kwargs):
            yield "Added task "
            yield "Buy groceries "
            yield "with ID 12."
            
        mock_stream.return_value = mock_async_gen()
        
        payload = {"task_id": 12, "title": "Buy groceries"}
        
        async def consume_stream():
            chunks = []
            async for chunk in broca.compile_response_stream(payload, epsilon=0.6):
                chunks.append(chunk)
            return "".join(chunks)
            
        res = asyncio.run(consume_stream())
        self.assertEqual(res, "Added task Buy groceries with ID 12.")

if __name__ == "__main__":
    unittest.main()
