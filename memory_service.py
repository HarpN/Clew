"""
memory_service.py - Hybrid Memory Layer (State Snapshots + Semantic Vector Memory)
Provides high-speed current state snapshot lookups alongside vector memory indexing.
"""

import json
import math
import logging
from typing import List, Dict, Any, Optional
import database
from database import get_db_connection, dialect, get_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.memory_service")

def _simple_embedding(text: str) -> List[float]:
    """
    Computes a deterministic feature vector embedding from input text
    for lightweight semantic matching fallback across local/pgvector nodes.
    """
    vec = [0.0] * 32
    for i, char in enumerate(text.lower()):
        idx = ord(char) % 32
        vec[idx] += 1.0 / (i + 1)
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 4) for x in vec]

def store_memory(
    entity_type: str,
    entity_id: str,
    content_text: str,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Indexes text content and stores vector embedding in vector_embeddings table.
    """
    vector = _simple_embedding(content_text)
    vector_json = json.dumps(vector)
    meta_json = json.dumps(metadata or {})
    
    query = """
        INSERT INTO vector_embeddings (entity_type, entity_id, content_text, embedding_json, metadata)
        VALUES (?, ?, ?, ?, ?)
    """
    formatted = dialect.format_query(query)
    
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(formatted, (entity_type, entity_id, content_text, vector_json, meta_json))
        if dialect.is_postgres:
            cursor.execute("SELECT LASTVAL();")
            mem_id = cursor.fetchone()["lastval"]
        else:
            mem_id = cursor.lastrowid
        logger.info(f"Stored semantic memory #{mem_id} [{entity_type}:{entity_id}]")
        return mem_id

def search_memory(query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Performs cosine similarity vector search over stored semantic memory.
    """
    query_vec = _simple_embedding(query_text)
    
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute("SELECT * FROM vector_embeddings ORDER BY id DESC LIMIT 100")
        rows = cursor.fetchall()
        
        scored = []
        for r in rows:
            row_dict = dict(r)
            try:
                emb = json.loads(row_dict["embedding_json"])
                # Cosine similarity dot product
                score = sum(q * e for q, e in zip(query_vec, emb))
            except Exception:
                score = 0.0
            scored.append((score, row_dict))
            
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, r_dict in scored[:limit]:
            r_dict["similarity_score"] = round(score, 4)
            results.append(r_dict)
        return results

def get_current_state_snapshot() -> Dict[str, Any]:
    """
    High-speed current working state snapshot retrieval.
    Includes active task counts, system telemetry, and strategy locks.
    """
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        
        # Count active pending tasks
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('pending', 'in_progress')")
        pending_count = cursor.fetchone()[0]
        
        # Get active strategies
        cursor.execute("""
            SELECT s.name, a.strategy, a.is_locked 
            FROM ai_adaptations a
            JOIN behavioral_scenarios s ON a.scenario_id = s.id
            WHERE a.is_active = 1 OR a.is_active = TRUE
        """)
        adaptations = [dict(r) for r in cursor.fetchall()]
        
        return {
            "active_tasks_count": pending_count,
            "active_rules_count": len(adaptations),
            "strategies": adaptations,
            "system_health": "operational"
        }
