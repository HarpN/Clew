"""
merkle_dag.py - Merkle DAG Versioning Layer for Clew GraphCRDT state.
Provides immutability, tamper-evident history, state diffing, and verification.
"""

import json
import datetime
from typing import Any, Dict, List, Set, Tuple, Optional
from ledger import compute_hash_hex
from crdt_engine import GraphCRDT, AddWinsORSet, LWWRegister, MultiValueRegister

def serialize_graph_crdt(crdt: GraphCRDT) -> dict:
    """
    Serializes a GraphCRDT instance into a JSON-serializable dictionary.
    """
    nodes_data = {
        "add_set": dict(crdt.nodes.add_set),  # tag -> node_id
        "remove_set": list(crdt.nodes.remove_set)
    }
    
    edges_data = {
        "add_set": {tag: list(edge) for tag, edge in crdt.edges.add_set.items()},
        "remove_set": list(crdt.edges.remove_set)
    }
    
    scalars_data = []
    for (target, prop_name), reg in crdt.scalars.items():
        scalars_data.append({
            "target": target,
            "property": prop_name,
            "value": reg.value,
            "timestamp": list(reg.timestamp) if reg.timestamp else None
        })
        
    mvr_data = []
    for (target, prop_name), mvr in crdt.semantic_mvr.items():
        entries_list = []
        for ts, val in mvr.entries.items():
            entries_list.append({
                "timestamp": list(ts),
                "value": val
            })
        mvr_data.append({
            "target": target,
            "property": prop_name,
            "entries": entries_list
        })
        
    return {
        "nodes": nodes_data,
        "edges": edges_data,
        "scalars": scalars_data,
        "semantic_mvr": mvr_data
    }

def deserialize_graph_crdt(data: dict) -> GraphCRDT:
    """
    Reconstructs a GraphCRDT instance from a serialized dictionary.
    """
    crdt = GraphCRDT()
    
    nodes_data = data.get("nodes", {})
    crdt.nodes.add_set = dict(nodes_data.get("add_set", {}))
    crdt.nodes.remove_set = set(nodes_data.get("remove_set", []))
    
    edges_data = data.get("edges", {})
    crdt.edges.add_set = {tag: tuple(edge) for tag, edge in edges_data.get("add_set", {}).items()}
    crdt.edges.remove_set = set(edges_data.get("remove_set", []))
    
    crdt.scalars = {}
    for item in data.get("scalars", []):
        key = (item["target"], item["property"])
        ts_raw = item["timestamp"]
        ts = tuple(ts_raw) if ts_raw else (0.0, 0, "")
        crdt.scalars[key] = LWWRegister(item["value"], ts)
        
    crdt.semantic_mvr = {}
    for item in data.get("semantic_mvr", []):
        key = (item["target"], item["property"])
        mvr = MultiValueRegister()
        for entry in item.get("entries", []):
            ts = tuple(entry["timestamp"])
            mvr.entries[ts] = entry["value"]
        crdt.semantic_mvr[key] = mvr
        
    return crdt

class MerkleCommit:
    """
    Represents a single immutable commit node in the Merkle DAG.
    """

    def __init__(
        self,
        parent_hashes: List[str],
        graph_snapshot: dict,
        author_node_id: str,
        message: str,
        timestamp: Optional[Any] = None,
        state_root_hash: Optional[str] = None,
        commit_hash: Optional[str] = None
    ):
        self.parent_hashes = parent_hashes
        self.graph_snapshot = graph_snapshot
        self.author_node_id = author_node_id
        self.message = message
        
        if timestamp is None:
            self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        else:
            self.timestamp = timestamp
            
        if state_root_hash is None:
            self.state_root_hash = self.compute_state_root()
        else:
            self.state_root_hash = state_root_hash
            
        if commit_hash is None:
            self.commit_hash = self.compute_hash()
        else:
            self.commit_hash = commit_hash

    def compute_state_root(self) -> str:
        """Computes root hash of the state snapshot."""
        encoded = json.dumps(self.graph_snapshot, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return compute_hash_hex(encoded)

    def compute_hash(self) -> str:
        """Computes deterministic hash digest over the commit's content."""
        data_to_hash = {
            "parent_hashes": self.parent_hashes,
            "timestamp": self.timestamp,
            "author_node_id": self.author_node_id,
            "message": self.message,
            "state_root_hash": self.state_root_hash,
            "graph_snapshot": self.graph_snapshot
        }
        encoded = json.dumps(data_to_hash, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return compute_hash_hex(encoded)


class MerkleDAG:
    """
    Directed Acyclic Graph (DAG) for Merkle commits tracking history.
    """

    def __init__(self):
        self.commits: Dict[str, MerkleCommit] = {}

    def add_commit(
        self,
        parent_hashes: List[str],
        graph_snapshot: dict,
        author_node_id: str,
        message: str,
        timestamp: Optional[Any] = None
    ) -> MerkleCommit:
        """Creates and registers a new MerkleCommit, establishing parent-child links."""
        commit = MerkleCommit(
            parent_hashes=parent_hashes,
            graph_snapshot=graph_snapshot,
            author_node_id=author_node_id,
            message=message,
            timestamp=timestamp
        )
        self.commits[commit.commit_hash] = commit
        return commit

    def get_commit(self, commit_hash: str) -> Optional[MerkleCommit]:
        """Retrieves a specific commit by hash."""
        return self.commits.get(commit_hash)

    def diff_commits(self, hash_a: str, hash_b: str) -> dict:
        """
        Compares two commit snapshots and returns added/removed/modified nodes, edges, and properties.
        """
        commit_a = self.get_commit(hash_a)
        commit_b = self.get_commit(hash_b)
        
        if not commit_a:
            raise ValueError(f"Commit not found: {hash_a}")
        if not commit_b:
            raise ValueError(f"Commit not found: {hash_b}")
            
        snap_a = commit_a.graph_snapshot
        snap_b = commit_b.graph_snapshot
        
        def get_active_nodes(snap):
            nodes_data = snap.get("nodes", {})
            add_set = nodes_data.get("add_set", {})
            remove_set = set(nodes_data.get("remove_set", []))
            return {elem for tag, elem in add_set.items() if tag not in remove_set}
            
        def get_active_edges(snap):
            edges_data = snap.get("edges", {})
            add_set = edges_data.get("add_set", {})
            remove_set = set(edges_data.get("remove_set", []))
            return {tuple(elem) for tag, elem in add_set.items() if tag not in remove_set}

        def get_resolved_properties(snap):
            props = {}
            for item in snap.get("scalars", []):
                props[(item["target"], item["property"])] = item["value"]
            for item in snap.get("semantic_mvr", []):
                # resolved values: list of values in entries
                values = [entry["value"] for entry in item.get("entries", [])]
                # sort to make list comparisons order-independent
                props[(item["target"], item["property"])] = sorted(values) if all(isinstance(v, (int, float, str)) for v in values) else values
            return props
            
        nodes_a = get_active_nodes(snap_a)
        nodes_b = get_active_nodes(snap_b)
        
        edges_a = get_active_edges(snap_a)
        edges_b = get_active_edges(snap_b)
        
        props_a = get_resolved_properties(snap_a)
        props_b = get_resolved_properties(snap_b)
        
        diff = {
            "nodes": {
                "added": list(nodes_b - nodes_a),
                "removed": list(nodes_a - nodes_b)
            },
            "edges": {
                "added": [list(e) for e in (edges_b - edges_a)],
                "removed": [list(e) for e in (edges_a - edges_b)]
            },
            "properties": {
                "added": [],
                "removed": [],
                "modified": []
            }
        }
        
        all_keys = set(props_a.keys()) | set(props_b.keys())
        for key in all_keys:
            target, prop_name = key
            val_a = props_a.get(key)
            val_b = props_b.get(key)
            
            if key in props_b and key not in props_a:
                diff["properties"]["added"].append({
                    "target": target,
                    "property": prop_name,
                    "value": val_b
                })
            elif key in props_a and key not in props_b:
                diff["properties"]["removed"].append({
                    "target": target,
                    "property": prop_name,
                    "value": val_a
                })
            elif val_a != val_b:
                diff["properties"]["modified"].append({
                    "target": target,
                    "property": prop_name,
                    "old_value": val_a,
                    "new_value": val_b
                })
                
        return diff

    def verify_dag_integrity(self) -> bool:
        """
        Traverses the DAG from leaf commits up to root commits, verifying that all hash links remain intact and tamper-free.
        """
        all_hashes = set(self.commits.keys())
        if not all_hashes:
            return True
            
        parent_hashes_set = set()
        for commit in self.commits.values():
            parent_hashes_set.update(commit.parent_hashes)
            
        leaves = all_hashes - parent_hashes_set
        if not leaves:
            return False
            
        visited = set()
        queue = list(leaves)
        
        while queue:
            current_hash = queue.pop(0)
            if current_hash in visited:
                continue
                
            commit = self.get_commit(current_hash)
            if not commit:
                return False
                
            # Verify the integrity of the commit's hash
            if commit.commit_hash != commit.compute_hash():
                return False
                
            # Verify parent hashes exist in our database
            for parent_hash in commit.parent_hashes:
                if parent_hash not in self.commits:
                    return False
                queue.append(parent_hash)
                
            visited.add(current_hash)
            
        # If there are unvisited disconnected parts or loops, verify them too.
        if visited != all_hashes:
            return False
            
        return True
