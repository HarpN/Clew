"""
event_store.py - Append-Only Event-Sourced Decision Catalog
Stores all architectural choices, intent events, personal decisions, and tradeoff contexts.
"""

import json
import logging
from typing import List, Dict, Any, Optional
import database
from database import get_db_connection, dialect, get_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.event_store")

def record_event(
    event_type: str,
    domain: str,
    title: str,
    description: Optional[str] = None,
    tradeoff_context: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Appends a new decision or architectural event to the ledger.
    """
    meta_json = json.dumps(metadata or {})
    query = """
        INSERT INTO event_store (event_type, domain, title, description, tradeoff_context, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    formatted = dialect.format_query(query)
    
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(formatted, (event_type, domain, title, description, tradeoff_context, meta_json))
        if dialect.is_postgres:
            cursor.execute("SELECT LASTVAL();")
            event_id = cursor.fetchone()["lastval"]
        else:
            event_id = cursor.lastrowid
        logger.info(f"Recorded event #{event_id}: [{domain}] {title}")
        return event_id

def get_events(domain: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves events filtered by domain or recent history.
    """
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        if domain:
            query = "SELECT * FROM event_store WHERE domain = ? ORDER BY id DESC LIMIT ?"
            cursor.execute(dialect.format_query(query), (domain, limit))
        else:
            query = "SELECT * FROM event_store ORDER BY id DESC LIMIT ?"
            cursor.execute(dialect.format_query(query), (limit,))
        
        rows = cursor.fetchall()
        result = []
        for r in rows:
            row_dict = dict(r)
            if isinstance(row_dict.get("metadata"), str):
                try:
                    row_dict["metadata"] = json.loads(row_dict["metadata"])
                except Exception:
                    pass
            result.append(row_dict)
        return result

def get_tradeoff_context(topic: str) -> Optional[str]:
    """
    Searches for tradeoff explanation context given a keyword or decision topic.
    """
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        query = "SELECT tradeoff_context FROM event_store WHERE (title LIKE ? OR description LIKE ?) AND tradeoff_context IS NOT NULL ORDER BY id DESC LIMIT 1"
        pattern = f"%{topic}%"
        cursor.execute(dialect.format_query(query), (pattern, pattern))
        row = cursor.fetchone()
        if row:
            return dict(row).get("tradeoff_context")
        return None

def get_decision_history(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Returns recent architectural or personal design decision events.
    """
    return get_events(limit=limit)
