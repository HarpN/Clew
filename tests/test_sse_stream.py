"""
tests/test_sse_stream.py - Integration test suite for FastAPI SSE Streaming (/api/chat/stream)
"""

import sys
import os
import unittest
import asyncio
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
from mobile_server import app

class TestSSEStreamEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()
        cls.client = TestClient(app)

    def test_01_sse_chat_stream_success(self):
        response = self.client.post(
            "/api/chat/stream",
            json={"prompt": "hello", "goal_tether_id": "mobile_default"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        
        lines = response.text.split("\n\n")
        non_empty_lines = [l.strip() for l in lines if l.strip()]
        
        # Must have at least init, token/data, and [DONE]
        self.assertTrue(len(non_empty_lines) >= 2)
        self.assertTrue(any("type" in line and "init" in line for line in non_empty_lines))
        self.assertTrue(any("[DONE]" in line for line in non_empty_lines))

    def test_02_sse_chat_stream_prompt(self):
        response = self.client.post(
            "/api/chat/stream",
            json={"prompt": "What is on my focus list for today?", "goal_tether_id": "mobile_default"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        
        text = response.text
        self.assertIn("data: {", text)
        self.assertIn("data: [DONE]", text)

if __name__ == "__main__":
    unittest.main()
