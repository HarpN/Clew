"""
tests/test_cognitive_brain.py - Unit test suite for CognitiveBrain split-brain orchestration layer.
"""

import sys
import os
import unittest
import asyncio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
import graph_memory
from brain import CognitiveBrain, clew_brain
from protocol import CommandResult

class TestCognitiveBrain(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()
        graph_memory.add_node("goal_tether_ai_split", "Split Brain AI Architecture Goal", "GOAL")

    def setUp(self):
        from unittest.mock import patch
        import datetime
        self.datetime_patcher = patch('orchestrator.datetime')
        self.mock_datetime = self.datetime_patcher.start()
        self.mock_datetime.now.return_value = datetime.datetime(2026, 7, 20, 12, 0, 0)
        self.mock_datetime.strptime = datetime.datetime.strptime

    def tearDown(self):
        self.datetime_patcher.stop()

    def test_01_process_thought_cycle_success(self):
        res = asyncio.run(
            clew_brain.process_thought_cycle(
                user_prompt="Build graph memory query module",
                goal_tether_id="goal_tether_ai_split"
            )
        )
        self.assertIsInstance(res, CommandResult)
        self.assertTrue(res.success)
        self.assertEqual(res.goal_tether_id, "goal_tether_ai_split")

    def test_02_process_thought_cycle_alignment_failure(self):
        res = asyncio.run(
            clew_brain.process_thought_cycle(
                user_prompt="Build graph memory query module",
                goal_tether_id="unregistered_tether_id_xyz"
            )
        )
        self.assertIsInstance(res, str)
        self.assertIn("Constraint Guard Veto", res)
        self.assertIn("Goal-Tether Alignment Failure", res)

if __name__ == "__main__":
    unittest.main()
