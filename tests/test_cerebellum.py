"""
tests/test_cerebellum.py - Integration tests for the Cerebellum action caching and hot-paths layer.
"""

import sys
import os
import unittest
import asyncio
import time
from unittest.mock import patch

# Ensure root workspace is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
from neuromorphic_subsystems import Cerebellum
from brain_orchestrator import CognitiveBrain

class TestCerebellumCaching(unittest.TestCase):
    def setUp(self):
        self.test_cache_path = "test_cerebellum_cache.json"
        if os.path.exists(self.test_cache_path):
            try:
                os.remove(self.test_cache_path)
            except Exception:
                pass
        database.init_db()

    def tearDown(self):
        if os.path.exists(self.test_cache_path):
            try:
                os.remove(self.test_cache_path)
            except Exception:
                pass

    def test_01_cache_learning_and_bypass_latency(self):
        # Instantiate brain with a custom test cache path
        brain = CognitiveBrain()
        brain.cerebellum.cache_path = self.test_cache_path
        brain.cerebellum.hot_paths = {}
        brain.cerebellum.learning_registry = {}
        brain.cerebellum.patterns = []
        brain.cerebellum.threshold = 5

        prompt = "add clean the room to chores"
        goal_tether_id = "goal_tether_chores"

        # Mock the database addition to keep it deterministic and fast, and mock datetime for daytime execution
        import datetime
        fake_now = datetime.datetime(2026, 7, 22, 10, 0, 0)
        with patch('orchestrator.orchestrator._execute_command', return_value={"task_id": 123, "title": "clean the room"}), \
             patch('constraint_guard.datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = fake_now
            mock_datetime.time = datetime.time
            # 1. Issue command 4 times: should NOT route via hot-path, but update registry
            for i in range(4):
                # Ensure no hot path has been compiled
                self.assertNotIn("add {} to chores", brain.cerebellum.hot_paths)
                
                is_success, friendly_res, intent, coords = asyncio.run(
                    brain.process_thought_cycle(prompt, goal_tether_id)
                )
                self.assertTrue(is_success)
                self.assertEqual(brain.cerebellum.learning_registry.get("add {} to chores"), i + 1)
                
                # Check that it did NOT bypass Frontal Lobe (intent is a full classified command from router)
                self.assertIsNotNone(intent)
                self.assertNotEqual(intent.reasoning, "Hot-path muscle memory match")

            # 2. Issue the 5th execution: should compile into hot_paths
            is_success, friendly_res, intent, coords = asyncio.run(
                brain.process_thought_cycle(prompt, goal_tether_id)
            )
            self.assertTrue(is_success)
            self.assertIn("add {} to chores", brain.cerebellum.hot_paths)
            self.assertEqual(brain.cerebellum.learning_registry.get("add {} to chores"), 5)

            # 3. Verify execute_hot_path returns direct execution parameters in under 1 ms
            start_time = time.perf_counter()
            matched = brain.cerebellum.execute_hot_path(prompt)
            duration_ms = (time.perf_counter() - start_time) * 1000

            self.assertIsNotNone(matched)
            domain, action, params = matched
            self.assertEqual(domain, "CHORES")
            self.assertEqual(action, "ADD_TASK")
            self.assertEqual(params.get("title"), "clean the room")
            self.assertLess(duration_ms, 1.0)
            
            # 4. Verify 6th execution hits the hot-path and returns direct stream in under 1 ms
            start_cycle = time.perf_counter()
            is_success, friendly_res, intent, coords = asyncio.run(
                brain.process_thought_cycle(prompt, goal_tether_id)
            )
            cycle_duration_ms = (time.perf_counter() - start_cycle) * 1000

            self.assertTrue(is_success)
            self.assertEqual(intent.reasoning, "Hot-path muscle memory match")
            self.assertLess(cycle_duration_ms, 50.0) # Using a generous bound for full cycle overhead, but execute_hot_path is < 1ms

if __name__ == "__main__":
    unittest.main()
