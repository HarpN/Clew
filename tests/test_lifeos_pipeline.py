"""
tests/test_lifeos_pipeline.py - Verification Suite for Clew LifeOS V2 Transition
Tests Pydantic intent schema validation, Constraint Guard governance,
<500ms Chit-Chat bypassing, Event Store logging, and Hybrid Memory indexing.
"""

import sys
import os
import time
import unittest

# Ensure root workspace is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
import protocol
from protocol import Domain, ActionType, Priority, EnergyLevel, IntentCommand
import event_store
import memory_service
from orchestrator import orchestrator, ConstraintGuard

class TestLifeOSPipeline(unittest.TestCase):

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

    def test_01_pydantic_schema_validation(self):
        valid_json = {
            "domain": "LOGISTICS",
            "action": "ADD_TASK",
            "reasoning": "User requested logistics task addition",
            "payload": {
                "title": "Clean deployment branch config",
                "priority": "P2",
                "energy_level": "medium"
            }
        }
        command = IntentCommand(**valid_json)
        self.assertEqual(command.domain, Domain.LOGISTICS)
        self.assertEqual(command.action, ActionType.ADD_TASK)

    def test_02_chitchat_latency_bypass(self):
        chitchat_payload = {
            "domain": "CHITCHAT",
            "action": "CHITCHAT",
            "reasoning": "Casual greeting",
            "payload": {"message": "Hello Clew!"}
        }
        start = time.time()
        result = orchestrator.process_intent(chitchat_payload)
        elapsed_ms = (time.time() - start) * 1000
        
        self.assertTrue(result.success)
        self.assertLess(result.latency_ms, 500.0)
        self.assertLess(elapsed_ms, 500.0)

    def test_03_constraint_guard_budget_limit(self):
        expensive_command = {
            "domain": "FINANCE",
            "action": "ADD_TASK",
            "reasoning": "Purchase server rack equipment",
            "payload": {
                "title": "Buy Rack Server",
                "budget_cost": 1200.00
            }
        }
        result = orchestrator.process_intent(expensive_command)
        self.assertFalse(result.success)
        self.assertTrue(result.blocked_by_constraint)
        self.assertIn("Budget Guard Violation", result.constraint_reason)

    def test_04_orchestrator_execution_and_event_store(self):
        task_intent = {
            "domain": "PROJECTS",
            "action": "ADD_TASK",
            "reasoning": "Log engineering focus task",
            "payload": {
                "title": "Refactor protocol middleware engine",
                "priority": "P1",
                "energy_level": "high",
                "context_tags": ["engineering", "v2"]
            }
        }
        result = orchestrator.process_intent(task_intent)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data.get("task_id"))
        
        # Verify Event Store record
        events = event_store.get_events(domain="PROJECTS", limit=5)
        self.assertGreater(len(events), 0)
        self.assertEqual(events[0]["domain"], "PROJECTS")

    def test_05_memory_service_hybrid_snapshot(self):
        snapshot = memory_service.get_current_state_snapshot()
        self.assertIn("active_tasks_count", snapshot)
        self.assertIn("active_rules_count", snapshot)
        self.assertEqual(snapshot["system_health"], "operational")

if __name__ == "__main__":
    unittest.main()
