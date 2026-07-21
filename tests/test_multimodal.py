"""
tests/test_multimodal.py - Unit test suite for Multi-Modal Visual Ingestion and SQLite vector fallback processing.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
from router import router

class TestMultimodalVisualIngestion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()

    def test_01_image_processing_fallback(self):
        # Test vision processing fallback when Ollama is not reachable
        dummy_bytes = b"fake_image_bytes_here"
        result = router.process_image_input(dummy_bytes, prompt="What is in this receipt?")
        self.assertIn("[VISION FALLBACK]", result)
        self.assertIn("What is in this receipt?", result)

    def test_02_store_and_query_visual_memory_sqlite_fallback(self):
        # Initialize test data
        tether_id = "test_tether_vision_01"
        
        # Clean up existing test visual memories
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM visual_memories WHERE tether_id = ?;", (tether_id,))

        # Embeddings are 1536-dimensional vectors
        emb_a = [0.0] * 1536
        emb_a[0] = 1.0  # Vector pointing along axis 0
        
        emb_b = [0.0] * 1536
        emb_b[1] = 1.0  # Vector pointing along axis 1
        
        # Store visual memory A
        id_a = database.store_visual_memory(
            tether_id=tether_id,
            summary="Receipt for $25 grocery purchase",
            ocr_data="Receipt details: $25 groceries",
            image_path="receipt.png",
            embedding=emb_a
        )
        self.assertGreater(id_a, 0)
        
        # Store visual memory B
        id_b = database.store_visual_memory(
            tether_id=tether_id,
            summary="System architecture overview diagram",
            ocr_data="Architecture diagram boxes",
            image_path="architecture.png",
            embedding=emb_b
        )
        self.assertGreater(id_b, 0)
        
        # 1. Query with query vector pointing along axis 0 (closest to A)
        query_v = [0.0] * 1536
        query_v[0] = 1.0
        
        results = database.query_visual_memories_by_vector(tether_id, query_v, limit=2)
        self.assertEqual(len(results), 2)
        
        # Memory A should be the first (closest, distance = 0.0)
        self.assertEqual(results[0]["image_path"], "receipt.png")
        self.assertAlmostEqual(results[0]["cosine_distance"], 0.0, places=4)
        
        # Memory B should be second (distance = 1.0)
        self.assertEqual(results[1]["image_path"], "architecture.png")
        self.assertAlmostEqual(results[1]["cosine_distance"], 1.0, places=4)

if __name__ == "__main__":
    unittest.main()
