"""
tests/test_self_optimization.py - Test Suite for Self-Optimization & Feedback Loop
Verifies unique command_id generation, feedback persistence, distillery proposed
optimizations (Human-in-the-Loop), Jinja2 prompt rendering, and autonomous confidence tuning.
"""

import sys
import os
import json
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
from protocol import Domain, ActionType, CommandResult
from orchestrator import orchestrator
from router import router, ModelTier, classify_tier, get_system_prompt
import distillery
import event_store

class TestSelfOptimization(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()

    def test_01_command_id_generation_and_feedback(self):
        query = "Create budget report for engineering tools"
        result = router.route(query)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.command_id)
        
        # Submit negative feedback with correction
        cmd_id = result.command_id
        fb_id = database.submit_intent_feedback(
            command_id=cmd_id,
            user_rating=1,
            correction_text="Do not auto-approve expenses over threshold without review"
        )
        self.assertIsNotNone(fb_id)

    def test_02_distillery_proposal_generation(self):
        summary = distillery.distillery.run_daily_distillation()
        self.assertGreater(summary["evaluated_feedback"], 0)
        self.assertGreater(summary["new_proposals_created"], 0)

        proposals = distillery.distillery.get_pending_proposals()
        self.assertGreater(len(proposals), 0)
        
        prop = proposals[0]
        self.assertEqual(prop["status"], "pending")
        self.assertIn("AUTO-OPTIMIZATION", prop["hint_text"])

    def test_03_human_in_the_loop_approval(self):
        proposals = distillery.distillery.get_pending_proposals()
        self.assertGreater(len(proposals), 0)
        
        prop_id = proposals[0]["id"]
        success = distillery.distillery.accept_optimization(prop_id)
        self.assertTrue(success)

        active_hints = distillery.load_active_hints()
        tier_hints = active_hints.get(proposals[0]["target_tier"], [])
        self.assertGreater(len(tier_hints), 0)

    def test_04_jinja2_prompt_rendering_with_hints(self):
        prompt_text = get_system_prompt(ModelTier.TIER_1_CODER)
        self.assertIn("CLEW SYSTEM PROMPT", prompt_text)

    def test_05_autonomous_confidence_tuning_fallback(self):
        # Explicitly set low confidence score history for FINANCE domain
        orchestrator.domain_confidence_history["FINANCE"] = [0.40, 0.50]
        
        tier, model = classify_tier("Review finance expense report", domain_hint=Domain.FINANCE)
        self.assertEqual(tier, ModelTier.TIER_1_CODER)

if __name__ == "__main__":
    unittest.main()
