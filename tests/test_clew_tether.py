"""
tests/test_clew_tether.py - Test Suite for Clew Tether Identity Synchronization Engine
Verifies Graph-Memory Layer nodes/edges, continuous standard-extraction,
Living Agent.md system prompt injection, Goal-Tether alignment checks, and export_memory().
"""

import sys
import os
import json
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
from protocol import Domain, ActionType, IntentCommand, CommandResult
import graph_memory
import distillery
from router import router, ModelTier, get_system_prompt
from orchestrator import orchestrator

class TestClewTether(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()

    def test_01_graph_memory_nodes_and_edges(self):
        # Create Entity nodes
        n1 = graph_memory.add_node("proj_clew_v2", "Clew V2 Architecture", "PROJECT", {"status": "active"})
        n2 = graph_memory.add_node("goal_low_latency", "Maintain <500ms Latency", "GOAL", {"target_ms": 500})
        n3 = graph_memory.add_node("rule_pydantic_only", "Pydantic Schema Validation Only", "RULE", {"category": "security"})
        
        self.assertEqual(n1, "proj_clew_v2")
        self.assertEqual(n2, "goal_low_latency")
        
        # Add Relationship edges
        e1 = graph_memory.add_edge("proj_clew_v2", "goal_low_latency", "ALIGNS_WITH", 1.0)
        e2 = graph_memory.add_edge("rule_pydantic_only", "goal_low_latency", "TRADEOFF_FOR", 0.9)
        self.assertIsNotNone(e1)
        self.assertIsNotNone(e2)

    def test_02_continuous_standard_extraction(self):
        # Log feedback with code correction
        cmd_id = "cmd_tether_test_01"
        database.submit_intent_feedback(
            command_id=cmd_id,
            user_rating=1,
            correction_text="Always use type annotations on function parameters"
        )
        
        # Run distillation to extract rule
        summary = distillery.distillery.run_daily_distillation()
        self.assertGreater(summary["evaluated_feedback"], 0)

        # Verify rule node was logged in graph_memory Style_Graph
        standards = graph_memory.get_style_graph_standards()
        self.assertTrue(any("Always use type annotations" in s for s in standards))

    def test_03_living_agent_prompt_injection(self):
        prompt_text = get_system_prompt(ModelTier.TIER_1_CODER)
        self.assertIn("Living Agent.md Standards", prompt_text)
        self.assertIn("Always use type annotations", prompt_text)

    def test_04_goal_tether_alignment_middleware_check(self):
        # 1. Valid goal tether ID check
        graph_memory.add_node("goal_tether_v2", "Clew V2 Handoff", "GOAL")
        valid_intent = {
            "goal_tether_id": "goal_tether_v2",
            "domain": "PROJECTS",
            "action": "ADD_TASK",
            "reasoning": "Adding aligned task for Clew V2 goal",
            "payload": {"title": "Deploy graph memory layer"}
        }
        res_valid = orchestrator.process_intent(valid_intent)
        self.assertTrue(res_valid.success)

        # 2. Invalid goal tether ID check
        invalid_intent = {
            "goal_tether_id": "non_existent_goal_xyz",
            "domain": "PROJECTS",
            "action": "ADD_TASK",
            "reasoning": "Attempting action on non-existent goal",
            "payload": {"title": "Unanchored execution"}
        }
        res_invalid = orchestrator.process_intent(invalid_intent)
        self.assertFalse(res_invalid.success)
        self.assertTrue(res_invalid.blocked_by_constraint)
        self.assertIn("Goal-Tether Alignment Failure", res_invalid.constraint_reason)

    def test_05_export_memory_utility(self):
        exported = graph_memory.export_memory()
        self.assertEqual(exported["version"], "2.0-ClewTether")
        self.assertIn("nodes_count", exported)
        self.assertIn("edges_count", exported)
        self.assertIn("nodes", exported)
        self.assertIn("edges", exported)
        self.assertIn("style_graph_standards", exported)
        self.assertGreater(exported["nodes_count"], 0)

if __name__ == "__main__":
    unittest.main()
