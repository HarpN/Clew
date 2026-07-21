"""
tests/test_hippocampus.py - Unit and integration tests for the Hippocampus experience consolidator.
"""

import sys
import os
import unittest
import asyncio
from unittest.mock import AsyncMock, patch

# Ensure root workspace is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
from neuromorphic_subsystems import Hippocampus

class TestHippocampus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()

    def setUp(self):
        # Clear chat timeline, adaptations, and audit log before each test
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_timeline;")
            cursor.execute("DELETE FROM ai_adaptations;")
            cursor.execute("DELETE FROM adaptation_audit_log;")

    def test_01_cosine_similarity_identical(self):
        h = Hippocampus()
        vectors, vocab = h._tokenize_and_vectorize([
            "No, don't use absolute paths",
            "No, don't use absolute paths"
        ])
        sim = h._cosine_similarity(vectors[0], vectors[1])
        self.assertAlmostEqual(sim, 1.0)

    def test_02_cosine_similarity_different(self):
        h = Hippocampus()
        vectors, vocab = h._tokenize_and_vectorize([
            "clean the kitchen laundry",
            "database queries in python"
        ])
        sim = h._cosine_similarity(vectors[0], vectors[1])
        self.assertLess(sim, 0.5)

    def test_03_clustering_corrections(self):
        h = Hippocampus(similarity_threshold=0.8)
        messages = [
            "No, don't use absolute paths",
            "please don't use absolute paths",
            "Run daily chores on weekend"
        ]
        clusters = h.cluster_corrections(messages)
        self.assertGreaterEqual(len(clusters), 2)
        
        path_cluster = None
        for c in clusters:
            if "No, don't use absolute paths" in c:
                path_cluster = c
                break
                
        self.assertIsNotNone(path_cluster)
        self.assertIn("please don't use absolute paths", path_cluster)

    @patch('router.ModelRouter')
    def test_04_consolidate_experience_loop(self, mock_router_class):
        mock_router = mock_router_class.return_value
        mock_router.execute_completion = AsyncMock(return_value="Always use relative paths instead of absolute paths.")

        database.add_chat_message("No, don't use absolute paths", speaker="user")
        database.add_chat_message("please don't use absolute paths", speaker="user")

        h = Hippocampus()
        consolidated = asyncio.run(h.consolidate_experience_loop(mock_router))
        self.assertEqual(consolidated, 1)

        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ai_adaptations;")
            adaptations = [dict(row) for row in cursor.fetchall()]
            self.assertEqual(len(adaptations), 1)
            self.assertIn("relative paths", adaptations[0]["strategy"])

            cursor.execute("SELECT * FROM adaptation_audit_log;")
            audits = [dict(row) for row in cursor.fetchall()]
            self.assertEqual(len(audits), 1)
            self.assertEqual(audits[0]["new_strategy_id"], adaptations[0]["id"])
            self.assertIn("absolute paths", audits[0]["triggering_telemetry"])

            cursor.execute("SELECT * FROM chat_timeline;")
            timeline = [dict(row) for row in cursor.fetchall()]
            self.assertEqual(len(timeline), 0)

    @patch('router.ModelRouter')
    def test_05_consolidate_experience_loop_locked_skips(self, mock_router_class):
        mock_router = mock_router_class.return_value
        mock_router.execute_completion = AsyncMock(return_value="Always use relative paths instead of absolute paths.")

        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ai_adaptations (scenario_id, strategy, is_active, is_locked) VALUES (1, ?, 1, 1);",
                ("Always use relative paths instead of absolute paths.",)
            )

        database.add_chat_message("No, don't use absolute paths", speaker="user")
        database.add_chat_message("please don't use absolute paths", speaker="user")

        h = Hippocampus()
        consolidated = asyncio.run(h.consolidate_experience_loop(mock_router))
        self.assertEqual(consolidated, 0)

        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chat_timeline;")
            timeline = [dict(row) for row in cursor.fetchall()]
            self.assertEqual(len(timeline), 2)

    def test_06_prune_expired_rules(self):
        from cron.optimize import prune_expired_rules
        import datetime
        
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(days=1)
        tomorrow = now + datetime.timedelta(days=1)
        
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            # 1. Insert an expired adaptation (unlocked)
            cursor.execute(
                database.dialect.format_query(
                    "INSERT INTO ai_adaptations (scenario_id, strategy, is_active, is_locked, expires_at) VALUES (1, ?, 1, 0, ?);"
                ),
                ("Expired temporary strategy", yesterday)
            )
            # 2. Insert a future adaptation (unlocked)
            cursor.execute(
                database.dialect.format_query(
                    "INSERT INTO ai_adaptations (scenario_id, strategy, is_active, is_locked, expires_at) VALUES (1, ?, 1, 0, ?);"
                ),
                ("Future temporary strategy", tomorrow)
            )
            # 3. Insert an expired adaptation (locked)
            cursor.execute(
                database.dialect.format_query(
                    "INSERT INTO ai_adaptations (scenario_id, strategy, is_active, is_locked, expires_at) VALUES (1, ?, 1, 1, ?);"
                ),
                ("Expired locked strategy", yesterday)
            )
            
        # Run prune
        prune_expired_rules()
        
        # Verify directly in the DB
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT strategy FROM ai_adaptations;")
            strategies = [row[0] for row in cursor.fetchall()]
            
        # 'Expired temporary strategy' should be deleted.
        self.assertNotIn("Expired temporary strategy", strategies)
        # 'Future temporary strategy' should NOT be deleted.
        self.assertIn("Future temporary strategy", strategies)
        # 'Expired locked strategy' should NOT be deleted because it is locked.
        self.assertIn("Expired locked strategy", strategies)

    def test_07_temporal_decay_filter(self):
        import datetime
        
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(days=1)
        tomorrow = now + datetime.timedelta(days=1)
        
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            # 1. Insert an expired adaptation (unlocked)
            cursor.execute(
                database.dialect.format_query(
                    "INSERT INTO ai_adaptations (scenario_id, strategy, is_active, is_locked, expires_at) VALUES (1, ?, 1, 0, ?);"
                ),
                ("Expired temporary strategy", yesterday)
            )
            # 2. Insert a future adaptation (unlocked)
            cursor.execute(
                database.dialect.format_query(
                    "INSERT INTO ai_adaptations (scenario_id, strategy, is_active, is_locked, expires_at) VALUES (1, ?, 1, 0, ?);"
                ),
                ("Future temporary strategy", tomorrow)
            )
            
        # Call get_behavioral_adaptations
        adaptations = database.get_behavioral_adaptations(only_active=False)
        strategies = [a["strategy"] for a in adaptations]
        
        # 'Expired temporary strategy' should NOT be returned (filtered out automatically)
        self.assertNotIn("Expired temporary strategy", strategies)
        # 'Future temporary strategy' should be returned
        self.assertIn("Future temporary strategy", strategies)

if __name__ == "__main__":
    unittest.main()
