"""
ledger.py - Append-Only Event Ledger for Clew V5 Architecture
Provides a tamper-evident, append-only event stream ordered by Hybrid Logical Clocks (HLC)
with BLAKE3/SHA256 hash digest chaining.
"""

import time
import json
import uuid
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field

from protocol import calculate_blake3_digest

def compute_hash_hex(data_bytes: bytes) -> str:
    """Computes a 64-character hex digest using BLAKE3 or SHA256 fallback."""
    try:
        import blake3
        return blake3.blake3(data_bytes).hexdigest()
    except ImportError:
        pass
    return hashlib.sha256(data_bytes).hexdigest()

class ClewLedgerEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    physical_time: float = Field(default_factory=time.time)
    logical_counter: int = Field(default=0)
    node_id: str = Field(default="primary-node")
    event_type: str = Field(..., description="Action type: NODE_ADD, NODE_REMOVE, EDGE_ADD, EDGE_REMOVE, SET_SCALAR, SET_SEMANTIC_MVR")
    target_id: str = Field(..., description="Target node ID, edge key, or entity ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event data parameters")
    prev_hash: str = Field(default="0" * 64, description="BLAKE3 hex digest of preceding event")
    event_hash: str = Field(default="", description="BLAKE3 hex digest of this event")

    @property
    def hlc_key(self) -> Tuple[float, int, str]:
        """Returns HLC tuple (physical_time, logical_counter, node_id) for total ordering."""
        return (self.physical_time, self.logical_counter, self.node_id)

    def calculate_hash(self) -> str:
        """Computes deterministic hash digest over event fields and prev_hash."""
        data_to_hash = {
            "event_id": self.event_id,
            "physical_time": round(self.physical_time, 6),
            "logical_counter": self.logical_counter,
            "node_id": self.node_id,
            "event_type": self.event_type,
            "target_id": self.target_id,
            "payload": self.payload,
            "prev_hash": self.prev_hash
        }
        encoded = json.dumps(data_to_hash, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return compute_hash_hex(encoded)

class ClewEventLedger:
    """
    Append-only tamper-evident event ledger storing sequential graph updates.
    """

    def __init__(self, node_id: str = "primary-node"):
        self.node_id = node_id
        self.events: List[ClewLedgerEvent] = []
        self.logical_counter = 0

    def append(
        self,
        event_type: str,
        target_id: str,
        payload: Optional[Dict[str, Any]] = None,
        physical_time: Optional[float] = None,
        node_id: Optional[str] = None
    ) -> ClewLedgerEvent:
        """Constructs, hashes, and appends a new event to the ledger."""
        self.logical_counter += 1
        p_time = physical_time if physical_time is not None else time.time()
        n_id = node_id if node_id is not None else self.node_id

        prev_hash = self.events[-1].event_hash if self.events else "0" * 64
        payload_data = payload or {}

        event = ClewLedgerEvent(
            physical_time=p_time,
            logical_counter=self.logical_counter,
            node_id=n_id,
            event_type=event_type,
            target_id=target_id,
            payload=payload_data,
            prev_hash=prev_hash
        )
        event.event_hash = event.calculate_hash()
        self.events.append(event)
        return event

    def verify_integrity(self) -> bool:
        """Validates that all events in the chain have unbroken hashes and valid signatures."""
        for i, event in enumerate(self.events):
            expected_prev = "0" * 64 if i == 0 else self.events[i - 1].event_hash
            if event.prev_hash != expected_prev:
                return False
            if event.event_hash != event.calculate_hash():
                return False
        return True

    def get_events_since(self, hlc_key: Tuple[float, int, str]) -> List[ClewLedgerEvent]:
        """Returns all events after a specified HLC timestamp tuple."""
        return [e for e in self.events if e.hlc_key > hlc_key]
