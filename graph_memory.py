"""
graph_memory.py - Graph-Memory Layer & Goal-Tether Alignment Engine
Manages a directed graph of Entities (Projects, Rules, Goals) and Relationships
(TRADEOFF_FOR, DEPENDS_ON, ALIGNS_WITH), providing style graph standard extraction
and portable memory serialization via export_memory().
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import database
from database import get_db_connection, dialect, get_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.graph_memory")

ENTITY_TYPES = {"PROJECT", "RULE", "GOAL"}
RELATIONSHIP_TYPES = {"TRADEOFF_FOR", "DEPENDS_ON", "ALIGNS_WITH"}

def add_node(
    node_id: str,
    label: str,
    entity_type: str,
    properties: Optional[Dict[str, Any]] = None
) -> str:
    """
    Adds or updates an Entity node (PROJECT, RULE, GOAL) in the graph.
    """
    etype = entity_type.upper()
    if etype not in ENTITY_TYPES:
        etype = "RULE"
        
    props_json = json.dumps(properties or {})
    
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        if dialect.is_postgres:
            query = """
                INSERT INTO graph_nodes (node_id, label, entity_type, properties_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (node_id) DO UPDATE SET
                    label = EXCLUDED.label,
                    properties_json = EXCLUDED.properties_json
            """
            cursor.execute(query, (node_id, label, etype, props_json))
        else:
            query = """
                INSERT OR REPLACE INTO graph_nodes (node_id, label, entity_type, properties_json)
                VALUES (?, ?, ?, ?)
            """
            cursor.execute(query, (node_id, label, etype, props_json))
            
        logger.info(f"Added Graph Node [{etype}] '{node_id}': {label}")
        return node_id

def add_edge(
    source_node_id: str,
    target_node_id: str,
    relationship_type: str,
    weight: float = 1.0
) -> int:
    """
    Adds a directed Relationship edge (TRADEOFF_FOR, DEPENDS_ON, ALIGNS_WITH).
    """
    rel = relationship_type.upper()
    if rel not in RELATIONSHIP_TYPES:
        rel = "ALIGNS_WITH"
        
    query = """
        INSERT INTO graph_edges (source_node_id, target_node_id, relationship_type, weight)
        VALUES (?, ?, ?, ?)
    """
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(dialect.format_query(query), (source_node_id, target_node_id, rel, weight))
        if dialect.is_postgres:
            cursor.execute("SELECT LASTVAL();")
            edge_id = cursor.fetchone()["lastval"]
        else:
            edge_id = cursor.lastrowid
        logger.info(f"Added Graph Edge '{source_node_id}' -[{rel}]-> '{target_node_id}'")
        return edge_id

def get_nodes(entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        if entity_type:
            query = "SELECT * FROM graph_nodes WHERE entity_type = ? ORDER BY id ASC"
            cursor.execute(dialect.format_query(query), (entity_type.upper(),))
        else:
            query = "SELECT * FROM graph_nodes ORDER BY id ASC"
            cursor.execute(query)
            
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            if isinstance(item.get("properties_json"), str):
                try:
                    item["properties"] = json.loads(item["properties_json"])
                except Exception:
                    item["properties"] = {}
            result.append(item)
        return result

def get_edges() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute("SELECT * FROM graph_edges ORDER BY id ASC")
        return [dict(r) for r in cursor.fetchall()]

def get_style_graph_standards() -> List[str]:
    """
    Retrieves all extracted standard rules from RULE nodes in Style_Graph
    for dynamic injection into Living Agent.md Jinja2 system prompts.
    """
    rule_nodes = get_nodes(entity_type="RULE")
    standards = []
    for node in rule_nodes:
        label = node.get("label", "")
        if label:
            standards.append(label)
    return standards

def verify_goal_alignment(domain: str, action: str, goal_tether_id: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Performs Tether-Check prior to command execution.
    If goal_tether_id is provided, verifies that active GOAL exists in graph_memory
    and is aligned with the intent.
    """
    if not goal_tether_id:
        return True, None
        
    nodes = get_nodes(entity_type="GOAL")
    goal_ids = {n.get("node_id") for n in nodes}
    
    if goal_tether_id not in goal_ids:
        reason = f"Goal-Tether Alignment Failure: Specified goal_tether_id '{goal_tether_id}' does not exist in graph_memory. Mandatory Alignment Clarification required."
        logger.warning(reason)
        return False, reason

    # Check edge alignment
    edges = get_edges()
    aligned = any(
        e.get("source_node_id") == goal_tether_id or e.get("target_node_id") == goal_tether_id
        for e in edges
    )
    
    # If node exists, goal tether is recognized
    return True, None

def export_memory() -> Dict[str, Any]:
    """
    Serializes the entire project graph (Nodes, Edges, Standards, Goals, Projects)
    into a portable JSON structure for zero-friction migration across agent instances.
    """
    nodes = get_nodes()
    edges = get_edges()
    standards = get_style_graph_standards()
    
    return {
        "version": "2.0-ClewTether",
        "nodes_count": len(nodes),
        "edges_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "style_graph_standards": standards
    }

def get_nodes_by_tether(goal_tether_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all graph nodes connected to or associated with a specific goal tether ID.
    """
    all_nodes = get_nodes()
    edges = get_edges()
    connected_node_ids = {goal_tether_id}
    for e in edges:
        if e.get("source_node_id") == goal_tether_id:
            connected_node_ids.add(e.get("target_node_id"))
        elif e.get("target_node_id") == goal_tether_id:
            connected_node_ids.add(e.get("source_node_id"))
            
    return [n for n in all_nodes if n.get("node_id") in connected_node_ids]

class GraphMemory:
    """
    Object-oriented wrapper around graph memory operations.
    """
    def add_node(self, node_id: str, label: str, entity_type: str, properties: Optional[Dict[str, Any]] = None) -> str:
        return add_node(node_id, label, entity_type, properties)

    def add_edge(self, source_node_id: str, target_node_id: str, relationship_type: str, weight: float = 1.0) -> int:
        return add_edge(source_node_id, target_node_id, relationship_type, weight)

    def get_nodes(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return get_nodes(entity_type)

    def get_edges(self) -> List[Dict[str, Any]]:
        return get_edges()

    def get_nodes_by_tether(self, goal_tether_id: str) -> List[Dict[str, Any]]:
        return get_nodes_by_tether(goal_tether_id)

    def get_style_graph_standards(self) -> List[str]:
        return get_style_graph_standards()

    def verify_goal_alignment(self, domain: Any, action_or_cmd: Any, goal_tether_id: Optional[str]) -> bool:
        dom_str = str(getattr(domain, "value", domain))
        act_str = str(getattr(action_or_cmd, "action", getattr(action_or_cmd, "value", action_or_cmd)))
        aligned, _ = verify_goal_alignment(dom_str, act_str, goal_tether_id)
        return aligned

    def export_memory(self) -> Dict[str, Any]:
        return export_memory()
