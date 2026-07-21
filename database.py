"""
database.py - Database Access & Persistence Layer for Personal AI Assistant
Supports both SQLite (WAL mode) for local single-node V1 deployment
and PostgreSQL (with ThreadedConnectionPool and RealDictCursor) for V2 scale-out deployment.
"""

import os
import sqlite3
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.database")

# Environment parameters for PostgreSQL V2 backend
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Conditional PostgreSQL driver initialization
PG_POOL = None
psycopg2_extras = None
if POSTGRES_HOST:
    try:
        from psycopg2 import pool, extras
        psycopg2_extras = extras
        PG_POOL = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            port=POSTGRES_PORT
        )
        logger.info("V2 Mode Enabled: Successfully initialized PostgreSQL ThreadedConnectionPool.")
    except ImportError:
        logger.error("V2 Postgres parameters detected but 'psycopg2' is not installed. Defaulting back to V1 SQLite.")

# SQLite Core Configuration (Safe local fallback / development)
DB_PATH = os.getenv("DB_PATH", "assistant.db")


class DialectManager:
    """
    Translates database dialects dynamically between SQLite and PostgreSQL.
    Eliminates query branch duplication by wrapping auto-increments and parameter bindings.
    """
    def __init__(self, is_postgres=False):
        self.is_postgres = is_postgres

    @property
    def placeholder(self):
        # SQLite uses '?', PostgreSQL uses '%s'
        return "%s" if self.is_postgres else "?"

    @property
    def serial_pk(self):
        # Dialect primary key auto-increment syntax
        return "SERIAL PRIMARY KEY" if self.is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"

    def format_query(self, query: str) -> str:
        """
        Adapts standard '?' bound queries directly to PostgreSQL '%s' on the fly.
        """
        if self.is_postgres:
            return query.replace("?", "%s")
        return query


dialect = DialectManager(is_postgres=(PG_POOL is not None))


def get_cursor(conn):
    """
    Returns a cursor configured with RealDictCursor for Postgres or standard cursor for SQLite.
    Ensures row-to-dictionary compatibility via dict(row).
    """
    if dialect.is_postgres and psycopg2_extras:
        return conn.cursor(cursor_factory=psycopg2_extras.RealDictCursor)
    return conn.cursor()


@contextmanager
def get_db_connection():
    """
    Context manager yielding active database connections. Supports pooled Postgres
    connections and local SQLite connections with forced WAL concurrency modes.
    Safely handles connection allocation errors without triggering UnboundLocalError.
    """
    conn = None
    if PG_POOL:
        try:
            conn = PG_POOL.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                PG_POOL.putconn(conn)
    else:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            conn.row_factory = sqlite3.Row
            # Enforce Write-Ahead Logging for SQLite concurrent threads
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA busy_timeout=5000;")
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()


@contextmanager
def get_db(db_path: str = DB_PATH):
    """
    Alias context manager for backward compatibility.
    """
    with get_db_connection() as conn:
        yield conn


def init_db(db_path: str = DB_PATH) -> None:
    """
    Creates tables safely under the active dialect. Drops legacy behavioral_rules flat table.
    """
    # [THREAT 2 PATCH] Cerebellar cache invalidation on database restart/reinitialization
    cache_file = "cerebellum_cache.json"
    if os.path.exists(cache_file):
        try:
            os.remove(cache_file)
            logger.info("[CEREBELLUM] Schema initialization or DB reboot detected. Stale motor cache cleared.")
        except Exception as e:
            logger.error(f"[CEREBELLUM] Failed to clear stale cache: {e}")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Clean up legacy flat rules table
        cursor.execute("DROP TABLE IF EXISTS behavioral_rules;")

        # 2. Context Trigger Scenarios
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS behavioral_scenarios (
                id {dialect.serial_pk},
                name VARCHAR(255) NOT NULL,
                description TEXT NOT NULL
            );
        """)

        # 3. Setup Strategy Adaptations (Added expires_at for Hippocampus over-fitting guard)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS ai_adaptations (
                id {dialect.serial_pk},
                scenario_id INTEGER NOT NULL,
                strategy TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                is_locked BOOLEAN DEFAULT 0,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Ensure expires_at column exists in case db already has active table (Dynamic Migration)
        try:
            cursor.execute("ALTER TABLE ai_adaptations ADD COLUMN expires_at TIMESTAMP;")
            logger.info("[MIGRATION] Added 'expires_at' column to table 'ai_adaptations'.")
        except Exception:
            pass # Column already exists

        # 4. Adaptation Audit Logging
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS adaptation_audit_log (
                id {dialect.serial_pk},
                scenario_id INTEGER NOT NULL,
                old_strategy_id INTEGER,
                new_strategy_id INTEGER,
                triggering_telemetry TEXT,
                llm_reasoning TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 5. Tasks Working State
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS tasks (
                id {dialect.serial_pk},
                title VARCHAR(255) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                priority INTEGER DEFAULT 2,
                energy_level VARCHAR(15) DEFAULT 'medium',
                context_tags TEXT DEFAULT '[]',
                due_date VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 6. Unified Chat Timeline
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS chat_timeline (
                id {dialect.serial_pk},
                source VARCHAR(30) NOT NULL DEFAULT 'desktop_text',
                speaker VARCHAR(15) NOT NULL DEFAULT 'user',
                content TEXT NOT NULL,
                audio_url TEXT,
                metadata TEXT DEFAULT '{{}}',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 7. Focus Blocks
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS focus_blocks (
                id {dialect.serial_pk},
                task_id INTEGER,
                title VARCHAR(255) NOT NULL,
                start_time VARCHAR(50) NOT NULL,
                end_time VARCHAR(50) NOT NULL,
                status VARCHAR(20) DEFAULT 'scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 8. Calendar Events
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id VARCHAR(100) PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                start_time VARCHAR(50) NOT NULL,
                end_time VARCHAR(50) NOT NULL,
                location VARCHAR(255),
                is_fixed INTEGER DEFAULT 1,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 9. Proactive Logistics
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS proactive_logistics (
                id {dialect.serial_pk},
                title VARCHAR(255) NOT NULL,
                details TEXT,
                target_date VARCHAR(50),
                status VARCHAR(20) DEFAULT 'pending',
                auto_trigger_rule TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 10. Execution Telemetry
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS execution_telemetry (
                id {dialect.serial_pk},
                task_id INTEGER,
                action VARCHAR(50) NOT NULL,
                time_of_day VARCHAR(20),
                energy_level VARCHAR(15),
                deferred_reason TEXT,
                telemetry_metadata TEXT DEFAULT '{{}}',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 11. Event-Sourced Decision Catalog
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS event_store (
                id {dialect.serial_pk},
                event_type VARCHAR(100) NOT NULL,
                domain VARCHAR(50) NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                tradeoff_context TEXT,
                metadata TEXT DEFAULT '{{}}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 12. Hybrid Vector Embeddings Storage
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS vector_embeddings (
                id {dialect.serial_pk},
                entity_type VARCHAR(50) NOT NULL,
                entity_id VARCHAR(100) NOT NULL,
                content_text TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                metadata TEXT DEFAULT '{{}}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 13. Intent Feedback Collection Table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS intent_feedback (
                id {dialect.serial_pk},
                command_id VARCHAR(100) NOT NULL,
                user_rating INTEGER NOT NULL,
                correction_text TEXT,
                auto_applied_bool BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 14. Graph Memory Nodes (Entities: PROJECT, RULE, GOAL)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id {dialect.serial_pk},
                node_id VARCHAR(100) UNIQUE NOT NULL,
                label VARCHAR(255) NOT NULL,
                entity_type VARCHAR(50) NOT NULL,
                properties_json TEXT DEFAULT '{{}}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 15. Graph Memory Edges (Relationships: TRADEOFF_FOR, DEPENDS_ON, ALIGNS_WITH)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS graph_edges (
                id {dialect.serial_pk},
                source_node_id VARCHAR(100) NOT NULL,
                target_node_id VARCHAR(100) NOT NULL,
                relationship_type VARCHAR(100) NOT NULL,
                weight FLOAT DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 16. pgvector extension registration (Postgres) and visual_memories table
        if dialect.is_postgres:
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                logger.info("[DB_INIT] Enabled pgvector extension successfully.")
            except Exception as ex:
                logger.error(f"[DB_INIT] Failed to create extension vector: {ex}")
        
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS visual_memories (
                id {dialect.serial_pk},
                tether_id VARCHAR(255),
                extracted_summary TEXT NOT NULL,
                raw_ocr_data TEXT,
                image_path TEXT,
                embedding {"vector(1536)" if dialect.is_postgres else "TEXT"},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


        # Seed default data if behavioral_scenarios is empty
        cursor.execute(dialect.format_query("SELECT COUNT(*) FROM behavioral_scenarios;"))
        count_row = cursor.fetchone()
        scenarios_count = count_row[0] if count_row else 0
        if scenarios_count == 0:
            scenarios = [
                ("Peak Productivity High Energy", "Focus windows occurring during late morning hours."),
                ("Late Night Technical Fatigue", "Logistical actions attempted past 10 PM on weekdays.")
            ]
            for name, desc in scenarios:
                cursor.execute(
                    dialect.format_query("INSERT INTO behavioral_scenarios (name, description) VALUES (?, ?);"),
                    (name, desc)
                )

            # Retrieve seeded scenario IDs
            cursor.execute(dialect.format_query("SELECT id FROM behavioral_scenarios ORDER BY id ASC;"))
            rows = cursor.fetchall()
            ids = [r[0] if isinstance(r, (tuple, list)) else r["id"] for r in rows]

            if len(ids) >= 2:
                adaptations = [
                    (ids[0], "Proactively schedule deep engineering blocks without interruptions.", True, False),
                    (ids[1], "Strictly defer complex technical implementations and suggest warm resting activities.", True, False)
                ]
                for s_id, strat, active, locked in adaptations:
                    act_val = True if dialect.is_postgres else 1
                    lock_val = False if dialect.is_postgres else 0
                    cursor.execute(
                        dialect.format_query("INSERT INTO ai_adaptations (scenario_id, strategy, is_active, is_locked) VALUES (?, ?, ?, ?);"),
                        (s_id, strat, act_val, lock_val)
                    )

            cursor.execute(
                dialect.format_query("INSERT INTO adaptation_audit_log (scenario_id, old_strategy_id, new_strategy_id, triggering_telemetry, llm_reasoning) VALUES (?, ?, ?, ?, ?);"),
                (ids[0], None, 1, "Initial seed", "Established baseline focus window strategy.")
            )
            logger.info("Successfully seeded primary behavioral scenarios and baseline adaptations.")

        # Schema migration check: Add triggering_telemetry if not present (SQLite concurrent run scenario)
        try:
            if not dialect.is_postgres:
                cursor.execute("PRAGMA table_info(adaptation_audit_log);")
                columns = [col[1] for col in cursor.fetchall()]
                if "triggering_telemetry" not in columns:
                    cursor.execute("ALTER TABLE adaptation_audit_log ADD COLUMN triggering_telemetry TEXT;")
                    logger.info("Migrated SQLite database: added triggering_telemetry column to adaptation_audit_log.")
        except Exception as migration_err:
            logger.warning(f"Failed to run schema migration on adaptation_audit_log: {migration_err}")


# --- Helper Data Access Functions ---

def add_task(
    title: str,
    description: Optional[str] = None,
    status: str = "pending",
    priority: int = 2,
    energy_level: str = "medium",
    context_tags: Optional[List[str]] = None,
    due_date: Optional[str] = None,
    db_path: str = DB_PATH
) -> int:
    tags_json = json.dumps(context_tags or [])
    query = dialect.format_query("""
    INSERT INTO tasks (title, description, status, priority, energy_level, context_tags, due_date)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (title, description, status, priority, energy_level, tags_json, due_date))
        if dialect.is_postgres:
            cursor.execute("SELECT LASTVAL();")
            return cursor.fetchone()[0]
        return cursor.lastrowid


def add_fluid_task(
    title: str,
    description: Optional[str] = None,
    priority: Any = 2,
    energy_level: str = "medium",
    context_tags: Optional[List[str]] = None,
    due_date: Optional[str] = None,
    status: str = "pending",
    db_path: str = DB_PATH
) -> int:
    """
    Wrapper for task creation, converting string priority ('P1', 'P2', 'P3') or int to numeric DB values.
    """
    if isinstance(priority, str):
        p_map = {"P1": 1, "P2": 2, "P3": 3, "1": 1, "2": 2, "3": 3}
        p_val = p_map.get(priority.upper(), 2)
    else:
        try:
            p_val = int(priority)
        except (ValueError, TypeError):
            p_val = 2

    return add_task(
        title=title,
        description=description,
        status=status,
        priority=p_val,
        energy_level=energy_level,
        context_tags=context_tags,
        due_date=due_date,
        db_path=db_path
    )


def get_tasks(status: Optional[str] = None, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    query = "SELECT * FROM tasks"
    params = []
    if status:
        query += f" WHERE status = {dialect.placeholder}"
        params.append(status)
    query += " ORDER BY priority ASC, id DESC"

    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        tasks = []
        for r in rows:
            task = dict(r)
            tags_raw = task.get("context_tags") or "[]"
            if isinstance(tags_raw, str):
                try:
                    task["context_tags"] = json.loads(tags_raw)
                except Exception:
                    task["context_tags"] = []
            tasks.append(task)
        return tasks


def update_task_status(task_id: int, status: str, db_path: str = DB_PATH) -> bool:
    query = dialect.format_query(f"UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (status, task_id))
        return cursor.rowcount > 0


def add_chat_message(
    content: str,
    source: str = "desktop_text",
    speaker: str = "user",
    audio_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db_path: str = DB_PATH
) -> int:
    metadata_json = json.dumps(metadata or {})
    query = dialect.format_query("""
    INSERT INTO chat_timeline (source, speaker, content, audio_url, metadata)
    VALUES (?, ?, ?, ?, ?)
    """)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (source, speaker, content, audio_url, metadata_json))
        if dialect.is_postgres:
            cursor.execute("SELECT LASTVAL();")
            return cursor.fetchone()[0]
        return cursor.lastrowid


def get_chat_timeline(limit: int = 50, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    query = f"SELECT * FROM chat_timeline ORDER BY id DESC LIMIT {dialect.placeholder}"
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        messages = []
        for r in reversed(rows):
            msg = dict(r)
            meta_raw = msg.get("metadata") or "{}"
            if isinstance(meta_raw, str):
                try:
                    msg["metadata"] = json.loads(meta_raw)
                except Exception:
                    msg["metadata"] = {}
            # Provide alias 'message' if 'content' is present for frontend backwards compatibility
            if "content" in msg and "message" not in msg:
                msg["message"] = msg["content"]
            messages.append(msg)
        return messages


def add_proactive_logistic(
    title: str,
    details: Optional[str] = None,
    target_date: Optional[str] = None,
    auto_trigger_rule: Optional[str] = None,
    db_path: str = DB_PATH
) -> int:
    query = dialect.format_query("""
    INSERT INTO proactive_logistics (title, details, target_date, auto_trigger_rule)
    VALUES (?, ?, ?, ?)
    """)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (title, details, target_date, auto_trigger_rule))
        if dialect.is_postgres:
            cursor.execute("SELECT LASTVAL();")
            return cursor.fetchone()[0]
        return cursor.lastrowid


def get_pending_logistics(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    query = "SELECT * FROM proactive_logistics WHERE status = 'pending' ORDER BY target_date ASC, id ASC"
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(query)
        return [dict(r) for r in cursor.fetchall()]


def log_telemetry(
    action: str,
    task_id: Optional[int] = None,
    time_of_day: Optional[str] = None,
    energy_level: Optional[str] = None,
    deferred_reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db_path: str = DB_PATH
) -> int:
    metadata_json = json.dumps(metadata or {})
    query = dialect.format_query("""
    INSERT INTO execution_telemetry (task_id, action, time_of_day, energy_level, deferred_reason, telemetry_metadata)
    VALUES (?, ?, ?, ?, ?, ?)
    """)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (task_id, action, time_of_day, energy_level, deferred_reason, metadata_json))
        if dialect.is_postgres:
            cursor.execute("SELECT LASTVAL();")
            return cursor.fetchone()[0]
        return cursor.lastrowid


def get_behavioral_adaptations(only_active: bool = True, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Retrieves adaptations joined dynamically with triggering context scenarios.
    Filters out expired adaptations automatically.
    """
    sql = """
        SELECT a.id, s.name as scenario_name, s.description, a.strategy, a.is_active, a.is_locked, a.expires_at 
        FROM ai_adaptations a
        JOIN behavioral_scenarios s ON a.scenario_id = s.id
    """
    conditions = []
    if only_active:
        conditions.append("a.is_active = TRUE" if dialect.is_postgres else "a.is_active = 1")
    
    # Enforce temporal decay check during fetches
    conditions.append("(a.expires_at IS NULL OR a.expires_at > CURRENT_TIMESTAMP)")
    
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(dialect.format_query(sql))
        # Ensure dict compatibility across both SQLite Row structures and Postgres dict cursors
        return [dict(row) for row in cursor.fetchall()]


def get_adaptation_audit_log(limit: int = 50, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Retrieves historical reverse-chronological adaptation telemetry and AI logic.
    """
    sql = f"""
        SELECT 
            l.id AS audit_log_id,
            l.scenario_id,
            s.name AS scenario_name,
            l.old_strategy_id,
            a_old.strategy AS old_strategy,
            l.new_strategy_id,
            a_new.strategy AS new_strategy,
            l.triggering_telemetry,
            l.llm_reasoning,
            l.created_at AS timestamp
        FROM adaptation_audit_log l
        LEFT JOIN behavioral_scenarios s ON l.scenario_id = s.id
        LEFT JOIN ai_adaptations a_old ON l.old_strategy_id = a_old.id
        LEFT JOIN ai_adaptations a_new ON l.new_strategy_id = a_new.id
        ORDER BY l.id DESC LIMIT {dialect.placeholder}
    """
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(dialect.format_query(sql), (limit,))
        return [dict(row) for row in cursor.fetchall()]


def update_adaptation_lock(adaptation_id: int, is_locked: bool, db_path: str = DB_PATH) -> bool:
    """
    Toggles the manual override lock flag on active strategies.
    """
    sql = "UPDATE ai_adaptations SET is_locked = ? WHERE id = ?;"
    val = True if is_locked else False if dialect.is_postgres else (1 if is_locked else 0)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(dialect.format_query(sql), (val, adaptation_id))
        return cursor.rowcount > 0


def revert_adaptation(audit_log_id: int, db_path: str = DB_PATH) -> bool:
    """
    Atomically reverts an autonomous adaptation by rolling back to its previous historical state.
    Safely handles edge cases where old_strategy_id is NULL (brand-new scenario).
    """
    fetch_sql = "SELECT scenario_id, old_strategy_id, new_strategy_id FROM adaptation_audit_log WHERE id = ?;"

    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(dialect.format_query(fetch_sql), (audit_log_id,))
        audit_record = cursor.fetchone()

        if not audit_record:
            logger.warning(f"Failed to execute rollback: Audit record {audit_log_id} not found.")
            return False

        old_strategy_id = audit_record["old_strategy_id"] if isinstance(audit_record, dict) else audit_record[1]
        new_strategy_id = audit_record["new_strategy_id"] if isinstance(audit_record, dict) else audit_record[2]
        scenario_id = audit_record["scenario_id"] if isinstance(audit_record, dict) else audit_record[0]

        val_inactive = False if dialect.is_postgres else 0
        val_active = True if dialect.is_postgres else 1

        # 1. Deactivate current (faulty) strategy suggestion
        if new_strategy_id is not None:
            cursor.execute(
                dialect.format_query("UPDATE ai_adaptations SET is_active = ? WHERE id = ?;"),
                (val_inactive, new_strategy_id)
            )

        # 2. Check for NULL in the old strategy column (safety guard for newly discovered scenarios)
        if old_strategy_id is not None:
            cursor.execute(
                dialect.format_query("UPDATE ai_adaptations SET is_active = ? WHERE id = ?;"),
                (val_active, old_strategy_id)
            )
            logger.info(f"Reverted scenario {scenario_id}: Swapped out strategy {new_strategy_id} back to {old_strategy_id}.")
        else:
            logger.info(f"Reverted scenario {scenario_id}: Strategy {new_strategy_id} was a brand-new scenario discovery. Disabled successfully.")

        return True


def update_logistic_status(logistic_id: int, status: str, db_path: str = DB_PATH) -> bool:
    query = dialect.format_query("UPDATE proactive_logistics SET status = ? WHERE id = ?")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (status, logistic_id))
        return cursor.rowcount > 0


def add_focus_block(
    title: str,
    start_time: str,
    end_time: str,
    task_id: Optional[int] = None,
    status: str = "scheduled",
    db_path: str = DB_PATH
) -> int:
    query = dialect.format_query("INSERT INTO focus_blocks (task_id, title, start_time, end_time, status) VALUES (?, ?, ?, ?, ?)")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (task_id, title, start_time, end_time, status))
        if dialect.is_postgres:
            cursor.execute("SELECT LASTVAL();")
            return cursor.fetchone()[0]
        return cursor.lastrowid


def get_focus_blocks(status: Optional[str] = None, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    query = "SELECT * FROM focus_blocks"
    params = []
    if status:
        query += f" WHERE status = {dialect.placeholder}"
        params.append(status)
    query += " ORDER BY start_time ASC"
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def add_calendar_event(
    event_id: str,
    title: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    is_fixed: int = 1,
    db_path: str = DB_PATH
) -> None:
    if dialect.is_postgres:
        query = """
        INSERT INTO calendar_events (id, title, description, start_time, end_time, location, is_fixed)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT(id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            start_time = EXCLUDED.start_time,
            end_time = EXCLUDED.end_time,
            location = EXCLUDED.location,
            is_fixed = EXCLUDED.is_fixed,
            synced_at = CURRENT_TIMESTAMP
        """
    else:
        query = """
        INSERT INTO calendar_events (id, title, description, start_time, end_time, location, is_fixed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            start_time = excluded.start_time,
            end_time = excluded.end_time,
            location = excluded.location,
            is_fixed = excluded.is_fixed,
            synced_at = CURRENT_TIMESTAMP
        """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (event_id, title, description, start_time, end_time, location, is_fixed))


def get_calendar_events(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    query = "SELECT * FROM calendar_events ORDER BY start_time ASC"
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(query)
        return [dict(r) for r in cursor.fetchall()]


def get_telemetry_logs(limit: int = 50, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    query = f"SELECT * FROM execution_telemetry ORDER BY id DESC LIMIT {dialect.placeholder}"
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        logs = []
        for r in rows:
            item = dict(r)
            meta_raw = item.get("telemetry_metadata") or "{}"
            if isinstance(meta_raw, str):
                try:
                    item["telemetry_metadata"] = json.loads(meta_raw)
                except Exception:
                    item["telemetry_metadata"] = {}
            logs.append(item)
        return logs


def check_wal_mode(db_path: str = DB_PATH) -> str:
    """
    Queries SQLite journal mode to verify WAL mode status, or returns postgres mode label.
    """
    if dialect.is_postgres:
        return "postgres"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        return str(mode).lower()

def submit_intent_feedback(command_id: str, user_rating: int, correction_text: Optional[str] = None) -> int:
    """
    Persists 1-click user rating and optional correction text to intent_feedback table.
    """
    query = """
        INSERT INTO intent_feedback (command_id, user_rating, correction_text)
        VALUES (?, ?, ?)
    """
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(dialect.format_query(query), (command_id, user_rating, correction_text))
        if dialect.is_postgres:
            cursor.execute("SELECT LASTVAL();")
            fb_id = cursor.fetchone()["lastval"]
        else:
            fb_id = cursor.lastrowid
        logger.info(f"Logged intent feedback #{fb_id} for command '{command_id}' (Rating: {user_rating}/5)")
        return fb_id

def get_intent_feedback(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves recent intent feedback items for self-optimization distillery processing.
    """
    query = "SELECT * FROM intent_feedback ORDER BY id DESC LIMIT ?"
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(dialect.format_query(query), (limit,))
        return [dict(r) for r in cursor.fetchall()]

def store_visual_memory(
    tether_id: str,
    summary: str,
    ocr_data: Optional[str] = None,
    image_path: Optional[str] = None,
    embedding: Optional[List[float]] = None,
    db_path: str = DB_PATH
) -> int:
    """
    Saves parsed visual summary, image path, OCR text and coordinates or vector embedding to the database.
    """
    emb_val = None
    if embedding is not None:
        if dialect.is_postgres:
            emb_val = '[' + ','.join(map(str, embedding)) + ']'
        else:
            emb_val = json.dumps(embedding)
            
    query = """
        INSERT INTO visual_memories (tether_id, extracted_summary, raw_ocr_data, image_path, embedding)
        VALUES (?, ?, ?, ?, ?)
    """
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(dialect.format_query(query), (tether_id, summary, ocr_data, image_path, emb_val))
        if dialect.is_postgres:
            cursor.execute("SELECT LASTVAL();")
            res_id = cursor.fetchone()["lastval"]
        else:
            res_id = cursor.lastrowid
        logger.info(f"Stored visual memory #{res_id} for tether '{tether_id}'")
        return res_id

def query_visual_memories_by_vector(
    tether_id: str,
    query_embedding: List[float],
    limit: int = 3,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """
    Returns top-k closest visual memories based on cosine similarity/distance of embeddings.
    """
    if dialect.is_postgres:
        emb_str = '[' + ','.join(map(str, query_embedding)) + ']'
        query = """
            SELECT id, tether_id, extracted_summary, raw_ocr_data, image_path, created_at, (embedding <=> %s::vector) AS cosine_distance
            FROM visual_memories
            WHERE tether_id = %s
            ORDER BY cosine_distance ASC
            LIMIT %s
        """
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            cursor.execute(query, (emb_str, tether_id, limit))
            return [dict(r) for r in cursor.fetchall()]
    else:
        # SQLite python fallback calculation for cosine distance
        import math
        query = "SELECT id, tether_id, extracted_summary, raw_ocr_data, image_path, embedding, created_at FROM visual_memories WHERE tether_id = ?"
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            cursor.execute(query, (tether_id,))
            rows = cursor.fetchall()
            
        results = []
        for r in rows:
            row_dict = dict(r)
            emb_raw = row_dict.pop("embedding", None)
            
            emb_list = None
            if emb_raw:
                try:
                    emb_list = json.loads(emb_raw)
                except Exception:
                    pass
            
            distance = 1.0
            if emb_list and len(emb_list) == len(query_embedding):
                dot_product = sum(u * v for u, v in zip(emb_list, query_embedding))
                norm_u = math.sqrt(sum(u * u for u in emb_list))
                norm_v = math.sqrt(sum(v * v for v in query_embedding))
                if norm_u > 0 and norm_v > 0:
                    cos_sim = dot_product / (norm_u * norm_v)
                    distance = 1.0 - cos_sim
                    
            row_dict["cosine_distance"] = distance
            results.append(row_dict)
            
        results.sort(key=lambda x: x["cosine_distance"])
        return results[:limit]


if __name__ == "__main__":
    print("Initializing Personal Assistant Database...")
    init_db()
    db_mode = check_wal_mode()
    print(f"Database initialized successfully. Active Backend Mode: {db_mode.upper()}")
