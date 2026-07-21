"""
version_engine.py - Version control engine for Clew GraphCRDT.
Manages snapshotting, commits, checkout rollbacks, and history traversal.
"""

from typing import Any, Dict, List, Optional
from crdt_engine import GraphCRDT
from merkle_dag import MerkleDAG, MerkleCommit, serialize_graph_crdt, deserialize_graph_crdt

class VersionEngine:
    """
    Manages versioning and atomic rollback of a GraphCRDT instance via a Merkle DAG.
    """

    def __init__(self, crdt_instance: GraphCRDT, node_id: str = "primary-node"):
        self.crdt = crdt_instance
        self.node_id = node_id
        self.dag = MerkleDAG()
        self.head_commit_hash: Optional[str] = None

    def commit(self, message: str) -> MerkleCommit:
        """
        Takes a full snapshot of the current GraphCRDT state and registers a new commit.
        """
        snapshot = serialize_graph_crdt(self.crdt)
        parent_hashes = [self.head_commit_hash] if self.head_commit_hash else []
        
        commit = self.dag.add_commit(
            parent_hashes=parent_hashes,
            graph_snapshot=snapshot,
            author_node_id=self.node_id,
            message=message
        )
        
        self.head_commit_hash = commit.commit_hash
        return commit

    def checkout(self, commit_hash: str) -> bool:
        """
        Atomically replaces/reconstructs the current GraphCRDT state to match the snapshot at commit_hash.
        """
        commit = self.dag.get_commit(commit_hash)
        if not commit:
            raise ValueError(f"Commit hash '{commit_hash}' not found in DAG.")
            
        # Deserialization check before mutation (ensuring atomicity)
        temp_crdt = deserialize_graph_crdt(commit.graph_snapshot)
        
        # Atomically swap internal structures
        self.crdt.nodes = temp_crdt.nodes
        self.crdt.edges = temp_crdt.edges
        self.crdt.scalars = temp_crdt.scalars
        self.crdt.semantic_mvr = temp_crdt.semantic_mvr
        
        self.head_commit_hash = commit_hash
        return True

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Traverses commits backwards from head_commit_hash to return a chronological list of commit summaries.
        """
        history = []
        if not self.head_commit_hash:
            return history
            
        visited = set()
        queue = [self.head_commit_hash]
        
        # Traverse backward to collect commit summaries
        while queue:
            curr_hash = queue.pop(0)
            if curr_hash in visited:
                continue
                
            commit = self.dag.get_commit(curr_hash)
            if not commit:
                continue
                
            summary = {
                "commit_hash": commit.commit_hash,
                "parent_hashes": commit.parent_hashes,
                "timestamp": commit.timestamp,
                "author_node_id": commit.author_node_id,
                "message": commit.message,
                "state_root_hash": commit.state_root_hash
            }
            history.append(summary)
            visited.add(curr_hash)
            
            for parent in commit.parent_hashes:
                queue.append(parent)
                
        # Reverse to return chronological order (oldest to newest)
        history.reverse()
        return history
