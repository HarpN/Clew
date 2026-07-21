"""
tests/test_reconciliation_arbiter.py - Test suite for ReconciliationEngine & LLM Arbiter
Verifies MVR divergence detection, mock LLM arbitration resolution, and no-op behavior on clean graphs.
"""

import json
import unittest
from unittest.mock import MagicMock, AsyncMock

from crdt_engine import GraphCRDT, MultiValueRegister
from reconciliation import ReconciliationEngine
from ledger import ClewEventLedger

class TestReconciliationArbiter(unittest.IsolatedAsyncioTestCase):

    def test_detect_mvr_divergence(self):
        """Simulates two concurrent updates on the same node property using different HLC node IDs and asserts find_divergences() extracts candidate values."""
        crdt = GraphCRDT()
        
        ledger_a = ClewEventLedger(node_id="node_a")
        ledger_b = ClewEventLedger(node_id="node_b")

        ledger_a.append("SET_SEMANTIC_MVR", target_id="doc_1", payload={"property": "summary", "value": "Summary from Node A"})
        ledger_b.append("SET_SEMANTIC_MVR", target_id="doc_1", payload={"property": "summary", "value": "Summary from Node B"})

        crdt.apply_ledger(ledger_a)
        crdt.apply_ledger(ledger_b)

        reconciler = ReconciliationEngine(crdt_instance=crdt)
        divergences = reconciler.find_divergences()

        self.assertEqual(len(divergences), 1)
        item = divergences[0]
        self.assertEqual(item["target_id"], "doc_1")
        self.assertEqual(item["property_key"], "summary")
        self.assertEqual(len(item["candidates"]), 2)
        values = [c["value"] for c in item["candidates"]]
        self.assertIn("Summary from Node A", values)
        self.assertIn("Summary from Node B", values)

    async def test_llm_arbiter_resolution(self):
        """Mocks LLM completion loop on a divergent MVR state and verifies reconcile_divergences() parses payload and resolves MVR divergence."""
        crdt = GraphCRDT()
        
        ledger_a = ClewEventLedger(node_id="node_a")
        ledger_b = ClewEventLedger(node_id="node_b")

        ledger_a.append("SET_SEMANTIC_MVR", target_id="task_99", payload={"property": "notes", "value": "Initial notes by Node A"})
        ledger_b.append("SET_SEMANTIC_MVR", target_id="task_99", payload={"property": "notes", "value": "Additional notes by Node B"})

        crdt.apply_ledger(ledger_a)
        crdt.apply_ledger(ledger_b)

        # Confirm initial state is divergent
        divergences_before = crdt.get_divergent_mvr_entries()
        self.assertIn(("task_99", "notes"), divergences_before)
        self.assertTrue(divergences_before[("task_99", "notes")].is_divergent())

        # Mock ModelRouter
        mock_router = MagicMock()
        mock_response = json.dumps({
            "resolutions": [
                {
                    "target_id": "task_99",
                    "property_key": "notes",
                    "winning_value": "Synthesized unified notes from A and B",
                    "rationale": "Combined critical info from both nodes"
                }
            ]
        })
        mock_router.execute_completion = AsyncMock(return_value=mock_response)

        reconciler = ReconciliationEngine(crdt_instance=crdt, router_instance=mock_router)
        resolved_count = await reconciler.reconcile_divergences()

        self.assertEqual(resolved_count, 1)
        mock_router.execute_completion.assert_called_once()
        
        # Verify MVR is no longer divergent and contains single unified value
        mvr = crdt.semantic_mvr[("task_99", "notes")]
        self.assertFalse(mvr.is_divergent())
        self.assertEqual(mvr.read_values(), ["Synthesized unified notes from A and B"])

    async def test_empty_reconciliation_noop(self):
        """Verifies calling reconcile_divergences() on a clean CRDT graph immediately returns 0 without calling the LLM."""
        crdt = GraphCRDT()
        
        # Add non-divergent scalar / MVR
        ledger_a = ClewEventLedger(node_id="node_a")
        ledger_a.append("SET_SCALAR", target_id="node_1", payload={"property": "status", "value": "DONE"})
        ledger_a.append("SET_SEMANTIC_MVR", target_id="node_1", payload={"property": "desc", "value": "Single description"})
        crdt.apply_ledger(ledger_a)

        mock_router = MagicMock()
        mock_router.execute_completion = AsyncMock()

        reconciler = ReconciliationEngine(crdt_instance=crdt, router_instance=mock_router)
        resolved_count = await reconciler.reconcile_divergences()

        self.assertEqual(resolved_count, 0)
        mock_router.execute_completion.assert_not_called()

if __name__ == "__main__":
    unittest.main()
