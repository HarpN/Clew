"""
crdt_engine.py - State-Based Graph CRDT Engine for Clew V5 Architecture
Implements Add-Wins Observed-Remove Sets (OR-Set) for nodes and edges,
Last-Write-Wins (LWW) Registers for scalar attributes, and Multi-Value Registers (MVR)
for divergent semantic property attributes.
"""

from typing import Any, Dict, Set, List, Tuple, Optional
from ledger import ClewLedgerEvent, ClewEventLedger

class AddWinsORSet:
    """
    Add-Wins Observed-Remove Set (OR-Set).
    Concurrent additions and deletions resolve in favor of addition (Add Wins).
    """

    def __init__(self):
        # Maps tag -> element
        self.add_set: Dict[str, Any] = {}
        # Set of removed tags
        self.remove_set: Set[str] = set()

    def add(self, element: Any, tag: str):
        """Adds element associated with a unique tag."""
        self.add_set[tag] = element

    def remove(self, element: Any) -> Set[str]:
        """Removes all currently observed tags for the element."""
        observed_tags = {tag for tag, elem in self.add_set.items() if elem == element}
        self.remove_set.update(observed_tags)
        return observed_tags

    def read(self) -> Set[Any]:
        """Returns set of active elements whose add tags have not been removed."""
        return {elem for tag, elem in self.add_set.items() if tag not in self.remove_set}

    def contains(self, element: Any) -> bool:
        """Checks if an element is currently active in the OR-Set."""
        return element in self.read()

    def merge(self, other: "AddWinsORSet"):
        """Unions add sets and remove sets from another OR-Set instance."""
        self.add_set.update(other.add_set)
        self.remove_set.update(other.remove_set)

class LWWRegister:
    """
    Last-Write-Wins (LWW) Register for scalar property updates.
    Resolves conflicts using HLC timestamp tuple (physical_time, logical_counter, node_id).
    """

    def __init__(self, initial_value: Any = None, timestamp: Tuple[float, int, str] = (0.0, 0, "")):
        self.value: Any = initial_value
        self.timestamp: Tuple[float, int, str] = timestamp

    def set(self, value: Any, timestamp: Tuple[float, int, str]):
        """Sets value if the new HLC timestamp is strictly higher."""
        if timestamp > self.timestamp:
            self.value = value
            self.timestamp = timestamp

    def merge(self, other: "LWWRegister"):
        """Merges another LWWRegister keeping the higher HLC timestamp value."""
        if other.timestamp > self.timestamp:
            self.value = other.value
            self.timestamp = other.timestamp

class MultiValueRegister:
    """
    Multi-Value Register (MVR) for divergent semantic attributes.
    Preserves concurrent un-reconciled updates across network splits.
    """

    def __init__(self):
        # Maps HLC timestamp tuple -> value
        self.entries: Dict[Tuple[float, int, str], Any] = {}

    def set(self, value: Any, timestamp: Tuple[float, int, str], causal_supersedes: Optional[Set[Tuple[float, int, str]]] = None):
        """
        Updates register with new value and timestamp.
        Removes any entries listed in causal_supersedes.
        """
        if causal_supersedes:
            for old_ts in causal_supersedes:
                self.entries.pop(old_ts, None)
        else:
            # Supersede older entries from the same node or strictly earlier timestamps if directly preceding
            to_remove = [ts for ts in self.entries if ts < timestamp and ts[2] == timestamp[2]]
            for old_ts in to_remove:
                self.entries.pop(old_ts, None)

        self.entries[timestamp] = value

    def is_divergent(self) -> bool:
        """Returns True if there are multiple concurrent, un-reconciled values."""
        return len(self.entries) > 1

    def read_values(self) -> List[Any]:
        """Returns list of all active concurrent values."""
        return list(self.entries.values())

    def resolve(self, selected_value: Any, resolution_timestamp: Tuple[float, int, str]):
        """Resolves divergent entries down to a single value."""
        self.entries.clear()
        self.entries[resolution_timestamp] = selected_value

    def merge(self, other: "MultiValueRegister"):
        """Unions entry maps from another MVR instance."""
        self.entries.update(other.entries)

class GraphCRDT:
    """
    State-Based Graph CRDT managing node/edge topology and entity attributes.
    """

    def __init__(self):
        self.nodes = AddWinsORSet()
        self.edges = AddWinsORSet()
        self.scalars: Dict[Tuple[str, str], LWWRegister] = {}
        self.semantic_mvr: Dict[Tuple[str, str], MultiValueRegister] = {}

    def apply_event(self, event: ClewLedgerEvent):
        """Applies a single ClewLedgerEvent to update CRDT state."""
        e_type = event.event_type
        target = event.target_id
        payload = event.payload
        ts = event.hlc_key

        if e_type == "NODE_ADD":
            self.nodes.add(target, event.event_id)
        elif e_type == "NODE_REMOVE":
            self.nodes.remove(target)
        elif e_type == "EDGE_ADD":
            source = payload.get("source", "")
            dest = payload.get("dest", "")
            label = payload.get("label", "REL")
            edge_tuple = (source, dest, label)
            self.edges.add(edge_tuple, event.event_id)
        elif e_type == "EDGE_REMOVE":
            source = payload.get("source", "")
            dest = payload.get("dest", "")
            label = payload.get("label", "REL")
            edge_tuple = (source, dest, label)
            self.edges.remove(edge_tuple)
        elif e_type == "SET_SCALAR":
            prop_name = payload.get("property", "attr")
            val = payload.get("value")
            key = (target, prop_name)
            if key not in self.scalars:
                self.scalars[key] = LWWRegister()
            self.scalars[key].set(val, ts)
        elif e_type == "SET_SEMANTIC_MVR":
            prop_name = payload.get("property", "description")
            val = payload.get("value")
            key = (target, prop_name)
            if key not in self.semantic_mvr:
                self.semantic_mvr[key] = MultiValueRegister()
            self.semantic_mvr[key].set(val, ts)

    def apply_ledger(self, ledger: ClewEventLedger):
        """Replays all events in a ledger in deterministic HLC order."""
        sorted_events = sorted(ledger.events, key=lambda e: e.hlc_key)
        for event in sorted_events:
            self.apply_event(event)

    def merge(self, other: "GraphCRDT"):
        """Merges state from another GraphCRDT instance."""
        self.nodes.merge(other.nodes)
        self.edges.merge(other.edges)

        for key, reg in other.scalars.items():
            if key not in self.scalars:
                self.scalars[key] = LWWRegister(reg.value, reg.timestamp)
            else:
                self.scalars[key].merge(reg)

        for key, mvr in other.semantic_mvr.items():
            if key not in self.semantic_mvr:
                self.semantic_mvr[key] = MultiValueRegister()
            self.semantic_mvr[key].merge(mvr)

    def get_divergent_mvr_entries(self) -> Dict[Tuple[str, str], MultiValueRegister]:
        """Returns map of entity property keys to MVRs containing divergent concurrent values."""
        return {key: mvr for key, mvr in self.semantic_mvr.items() if mvr.is_divergent()}
