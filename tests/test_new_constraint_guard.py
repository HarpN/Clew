import sys
import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
from constraint_guard import ConstraintGuard
from brain_orchestrator import CognitiveBrain

class TestNewConstraintGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        # Seed test task in case it doesn't exist
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            # Clear existing tasks to have a predictable test environment
            cursor.execute("DELETE FROM tasks WHERE title = 'Duplicate Task Test';")
            cursor.execute(
                database.dialect.format_query(
                    "INSERT INTO tasks (title, priority, energy_level, status) VALUES (?, 2, 'medium', 'pending');"
                ),
                ('Duplicate Task Test',)
            )

    def test_greeting_fast_path(self):
        brain = CognitiveBrain()
        # Test that hi, status, yo are caught by fast path
        for greeting in ["hi", "wake up", "yo", "status"]:
            is_success, friendly_res, intent, coords = asyncio.run(brain.process_thought_cycle(greeting, "goal_tether_chores"))
            self.assertTrue(is_success)
            self.assertEqual(friendly_res, "Active. Ready to navigate the labyrinth. What are we building?")
            self.assertIsNone(intent)

    @patch('constraint_guard.datetime')
    def test_late_night_fatigue_triggered(self, mock_datetime):
        # Mock time to 11:30 PM (23:30)
        mock_datetime.datetime.now.return_value = datetime.datetime(2026, 7, 20, 23, 30, 0)
        mock_datetime.time = datetime.time

        guard = ConstraintGuard()
        
        # High energy keywords trigger pre-flight veto
        is_valid, reason = guard.verify_pre_flight(
            intent_domain="PROJECTS",
            action="ADD_TASK",
            params={"title": "Refactor database pool config", "energy_level": "medium"}
        )
        self.assertFalse(is_valid)
        self.assertIn("Late-Night Fatigue Policy active", reason)

        # High energy level parameter triggers pre-flight veto
        is_valid, reason = guard.verify_pre_flight(
            intent_domain="PROJECTS",
            action="ADD_TASK",
            params={"title": "Clean room", "energy_level": "high"}
        )
        self.assertFalse(is_valid)
        self.assertIn("Late-Night Fatigue Policy active", reason)

        # High energy domains trigger pre-flight veto
        is_valid, reason = guard.verify_pre_flight(
            intent_domain="CODER",
            action="ADD_TASK",
            params={"title": "simple task", "energy_level": "low"}
        )
        self.assertFalse(is_valid)
        self.assertIn("Late-Night Fatigue Policy active", reason)

    @patch('constraint_guard.datetime')
    def test_late_night_fatigue_passed_during_day(self, mock_datetime):
        # Mock time to 12:00 PM
        mock_datetime.datetime.now.return_value = datetime.datetime(2026, 7, 20, 12, 0, 0)
        mock_datetime.time = datetime.time

        guard = ConstraintGuard()
        is_valid, reason = guard.verify_pre_flight(
            intent_domain="PROJECTS",
            action="ADD_TASK",
            params={"title": "Refactor database pool config", "energy_level": "medium"}
        )
        self.assertTrue(is_valid)
        self.assertEqual(reason, "")

    def test_financial_bounds(self):
        guard = ConstraintGuard()
        # Over standard limit
        is_valid, reason = guard.verify_pre_flight(
            intent_domain="FINANCE",
            action="ADD_TRANSACTION",
            params={"amount": 550.00, "category": "hosting"}
        )
        self.assertFalse(is_valid)
        self.assertIn("Financial Transaction Guard veto", reason)
        self.assertIn("exceeds standard safety limit of $500.00", reason)

        # Under limit
        is_valid, reason = guard.verify_pre_flight(
            intent_domain="FINANCE",
            action="ADD_TRANSACTION",
            params={"amount": 49.99, "category": "hosting"}
        )
        self.assertTrue(is_valid)
        self.assertEqual(reason, "")

    def test_duplicate_task_guard(self):
        guard = ConstraintGuard()
        
        # Test duplicate matches
        is_valid, reason = guard.verify_pre_flight(
            intent_domain="PROJECTS",
            action="ADD_TASK",
            params={"title": "Duplicate Task Test"}
        )
        self.assertFalse(is_valid)
        self.assertIn("Task State Redundancy", reason)

        # Test unique matches
        is_valid, reason = guard.verify_pre_flight(
            intent_domain="PROJECTS",
            action="ADD_TASK",
            params={"title": "Totally Unique Task Name"}
        )
        self.assertTrue(is_valid)

    @patch('brain_orchestrator.ModelRouter')
    def test_brain_orchestrator_veto_handling(self, mock_router_class):
        # Setup mock intent classification to return a project add task
        mock_router = mock_router_class.return_value
        mock_intent = MagicMock()
        mock_intent.domain = "CODER"
        mock_intent.action = "ADD_TASK"
        
        async def mock_classify(*args, **kwargs):
            return mock_intent
        mock_router.classify_intent = mock_classify

        # Force late night to trigger veto
        with patch('constraint_guard.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value = datetime.datetime(2026, 7, 20, 23, 0, 0)
            mock_datetime.time = datetime.time

            brain = CognitiveBrain()
            is_success, friendly_res, intent_or_reason, coords = asyncio.run(
                brain.process_thought_cycle("Refactor pool", "goal_tether_chores")
            )
            
            self.assertFalse(is_success)
            self.assertIn("Constraint Guard Veto", friendly_res)
            self.assertEqual(intent_or_reason, "MANUAL_REVIEW_REQUIRED")

if __name__ == "__main__":
    unittest.main()
