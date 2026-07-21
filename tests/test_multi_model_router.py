"""
tests/test_multi_model_router.py - Test Suite for Multi-Model Agentic Router
Verifies Tier 1 Coder vs Tier 2 Generalist classification, protocol enforcement,
and reflective feedback tracking.
"""

import sys
import os
import unittest

# Ensure root workspace is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
from protocol import Domain, ActionType, CommandResult
from router import router, ModelTier, classify_tier, CODER_MODEL, GENERALIST_MODEL
import reflective_job

class TestMultiModelRouter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()

    def setUp(self):
        from unittest.mock import patch
        import datetime
        self.datetime_patcher = patch('orchestrator.datetime')
        self.mock_datetime = self.datetime_patcher.start()
        self.mock_datetime.now.return_value = datetime.datetime(2026, 7, 20, 12, 0, 0)
        self.mock_datetime.strptime = datetime.datetime.strptime

    def tearDown(self):
        self.datetime_patcher.stop()

    def test_01_tier_1_coder_classification(self):
        query = "Refactor database query logic in python script"
        tier, model = classify_tier(query)
        self.assertEqual(tier, ModelTier.TIER_1_CODER)
        self.assertEqual(model, CODER_MODEL)

    def test_02_tier_2_generalist_classification(self):
        query = "Remind me to do laundry tomorrow morning"
        tier, model = classify_tier(query)
        self.assertEqual(tier, ModelTier.TIER_2_GENERALIST)
        self.assertEqual(model, GENERALIST_MODEL)

    def test_03_protocol_enforcement_and_routing(self):
        coder_query = "Write docker container deployment config"
        res_coder = router.route(coder_query)
        
        self.assertTrue(res_coder.success)
        self.assertEqual(res_coder.tier, ModelTier.TIER_1_CODER.value)
        self.assertEqual(res_coder.model_used, CODER_MODEL)

        generalist_query = "Track budget cost for $25 grocery purchase"
        res_gen = router.route(generalist_query)
        
        self.assertTrue(res_gen.success)
        self.assertEqual(res_gen.tier, ModelTier.TIER_2_GENERALIST.value)
        self.assertEqual(res_gen.model_used, GENERALIST_MODEL)

    def test_04_reflective_job_feedback_loop(self):
        # Trigger routed queries
        router.route("Fix python bug in database.py", domain_hint=Domain.CODE)
        router.route("Clean kitchen and organize chores list", domain_hint=Domain.CHORES)
        
        summary = reflective_job.run_reflective_analysis(limit=50)
        
        self.assertIsInstance(summary, dict)
        self.assertGreater(len(summary), 0)
        
        # Check that metrics contain reported tiers
        tiers_reported = [v.get("tier") for v in summary.values()]
        self.assertTrue(any(ModelTier.TIER_1_CODER.value in t for t in tiers_reported if t))

if __name__ == "__main__":
    unittest.main()
